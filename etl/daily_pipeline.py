import os
import glob
import hashlib
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
import polars as pl
from dagster import op, job, schedule, RunRequest, Failure, Out, DefaultScheduleStatus

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://postgres:password@age_db:5432/age_prod_01")

# Use standard mount location, fallback to relative local path
INPUT_DIR = "/opt/dagster/input_data" if os.path.exists("/opt/dagster/input_data") else os.path.join(os.path.dirname(__file__), "..", "input_data")

def get_db_connection():
    try:
        return psycopg2.connect(POSTGRES_URI)
    except psycopg2.OperationalError:
        # Fallback to local host mapped port 5433
        return psycopg2.connect("postgresql://postgres:password@localhost:5433/age_prod_01")

@op(out={"filepath": Out(str)})
def check_file_availability(context):
    today_str = datetime.now().strftime("%Y%m%d")
    
    # Looking for YYYYMMDD_CUST_TNG.csv or YYYYMMDD_cust_TNG.csv
    search_pattern = os.path.join(INPUT_DIR, f"{today_str}_*ust_TNG.csv")
    files = glob.glob(search_pattern)
    
    if not files:
        # Fallback to specifically what the user mentioned if the wildcard fails
        fixed_path1 = os.path.join(INPUT_DIR, f"{today_str}_CUST_TNG.csv")
        fixed_path2 = os.path.join(INPUT_DIR, f"{today_str}_cust_TNG.csv")
        if os.path.exists(fixed_path1): files.append(fixed_path1)
        elif os.path.exists(fixed_path2): files.append(fixed_path2)

    if not files:
        raise Failure(f"Data file for {today_str} not found in {INPUT_DIR}. Expected pattern: {today_str}_CUST_TNG.csv")
        
    filepath = files[0]
    context.log.info(f"File found and verified for processing: {filepath}")
    return filepath

@op
def load_csv_to_postgres(context, filepath: str) -> str:
    context.log.info(f"Reading and formatting {filepath} using Polars")
    df = pl.read_csv(filepath, infer_schema_length=10000, ignore_errors=True)
    
    df = df.rename({
        "customer num": "customer_num",
        "txn currency_amount": "txn_currency_amount",
        "Txn Type": "txn_type"
    })
    
    df = df.drop_nulls(subset=["txn_ref_no"])
    
    # Idempotent txn_hash
    df = df.with_columns(
        pl.concat_str([
            pl.col("customer_num").cast(str),
            pl.col("txn_date").cast(str),
            pl.col("txn_ref_no").cast(str),
            pl.col("txn_currency_amount").cast(str)
        ]).map_elements(lambda s: hashlib.sha256(s.encode()).hexdigest(), return_dtype=pl.String).alias("txn_hash")
    )
    
    # Strip garbage prefixes
    def clean_cp(s):
        if not s: return "UNKNOWN"
        s = str(s).strip()
        for p in ["PAY TO ", "PAY FROM ", "(FOREIGN TXN FEE) "]:
            if s.startswith(p): s = s.replace(p, "")
        return s.strip()

    df = df.with_columns(
        pl.col("Counterparties").map_elements(clean_cp, return_dtype=pl.String).alias("counterparty_id")
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Customers
    customers = df.select("customer_num").unique().to_dicts()
    execute_values(cursor, "INSERT INTO core.customers (customer_num) VALUES %s ON CONFLICT (customer_num) DO NOTHING", [(str(c["customer_num"]),) for c in customers])
    
    # 2. Counterparties
    counterparties = df.select("counterparty_id", pl.col("txn_type").str.contains("MERCHANT").alias("is_merchant")).unique("counterparty_id").to_dicts()
    execute_values(cursor, "INSERT INTO core.counterparties (counterparty_id, counterparty_name, is_merchant) VALUES %s ON CONFLICT (counterparty_id) DO NOTHING", [(str(c["counterparty_id"]), str(c["counterparty_id"]), bool(c["is_merchant"])) for c in counterparties])
    
    # 3. Transactions
    txns = df.to_dicts()
    def safe_float(v):
        try: return float(v)
        except: return 0.0

    execute_values(
        cursor,
        "INSERT INTO core.transactions (txn_hash, customer_num, counterparty_id, txn_date, txn_ref_no, txn_country, txn_currency, txn_currency_amount, txn_amount_in_hkd, cdi_code, txn_type, source_filename) VALUES %s ON CONFLICT (txn_hash) DO NOTHING",
        [(str(t["txn_hash"]), str(t["customer_num"]), str(t["counterparty_id"]), str(t["txn_date"]), str(t["txn_ref_no"]), str(t["txn_country"]), str(t["txn_currency"]), safe_float(t["txn_currency_amount"]), safe_float(t["txn_amount_in_hkd"]), str(t["cdi_code"]), str(t["txn_type"]), os.path.basename(filepath)) for t in txns]
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    context.log.info("Relational load to core PostgreSQL completed.")
    return filepath

@op
def verify_data_load(context, filepath: str) -> str:
    filename = os.path.basename(filepath)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM core.transactions WHERE source_filename = %s", (filename,))
    count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    if count == 0:
        raise Failure(f"Data verification failed! Expected records for file '{filename}', but got 0 in Postgres.")
        
    context.log.info(f"Verification Success: {count} valid records loaded from '{filename}'.")
    return filepath

@op
def update_graph_model(context, filepath: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SET search_path = ag_catalog, \"$user\", public;")
    
    # Apply standard Age MERGE definitions to ensure network topological updates
    sql_script = """
    DO $$
    DECLARE
        c record;
        cp record;
        t record;
    BEGIN
        FOR c IN SELECT customer_num FROM core.customers LOOP
            EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ MERGE (n:Customer {id: ''%s''}) $cypher$) AS (a agtype);', c.customer_num);
        END LOOP;

        FOR cp IN SELECT counterparty_id, is_merchant FROM core.counterparties LOOP
            IF cp.is_merchant THEN
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ MERGE (m:Merchant {id: ''%s''}) $cypher$) AS (a agtype);', cp.counterparty_id);
            ELSE
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ MERGE (n:Counterparty {id: ''%s''}) $cypher$) AS (a agtype);', cp.counterparty_id);
            END IF;
        END LOOP;
        
        FOR t IN SELECT txn.txn_hash, txn.customer_num, txn.counterparty_id, txn.cdi_code, txn.txn_amount_in_hkd, cp_tab.is_merchant AS is_merchant, COALESCE(EXTRACT(EPOCH FROM txn.txn_date)::bigint, 0) AS ts_epoch
                 FROM core.transactions txn
                 JOIN core.counterparties cp_tab ON txn.counterparty_id = cp_tab.counterparty_id LOOP
            IF t.cdi_code = 'D' THEN
                IF t.is_merchant THEN
                    EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ MATCH (src:Customer {id: ''%s''}), (dst:Merchant {id: ''%s''}) MERGE (src)-[e:PAID {txn_hash: ''%s'', amount: %s}]->(dst) SET e.ts = %s $cypher$) AS (a agtype);', t.customer_num, t.counterparty_id, t.txn_hash, t.txn_amount_in_hkd, t.ts_epoch);
                ELSE
                    EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ MATCH (src:Customer {id: ''%s''}), (dst:Counterparty {id: ''%s''}) MERGE (src)-[e:TRANSFERRED {txn_hash: ''%s'', amount: %s}]->(dst) SET e.ts = %s $cypher$) AS (a agtype);', t.customer_num, t.counterparty_id, t.txn_hash, t.txn_amount_in_hkd, t.ts_epoch);
                END IF;
            ELSE
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ MATCH (src:Counterparty {id: ''%s''}), (dst:Customer {id: ''%s''}) MERGE (src)-[e:TRANSFERRED {txn_hash: ''%s'', amount: %s}]->(dst) SET e.ts = %s $cypher$) AS (a agtype);', t.counterparty_id, t.customer_num, t.txn_hash, t.txn_amount_in_hkd, t.ts_epoch);
            END IF;
        END LOOP;
    END
    $$;
    """
    
    cursor.execute(sql_script)
    conn.commit()
    cursor.close()
    conn.close()
    
    context.log.info("Graph topology completely synchronized with updated Postgres records.")
    return filepath

@op
def rename_to_ok(context, filepath: str):
    ok_filepath = filepath + ".OK"
    os.rename(filepath, ok_filepath)
    context.log.info(f"Workflow Complete. Input file protected and renamed to: {ok_filepath}")

@job
def daily_update_job():
    verified_file = check_file_availability()
    loaded_file = load_csv_to_postgres(verified_file)
    validated_file = verify_data_load(loaded_file)
    graph_updated_file = update_graph_model(validated_file)
    rename_to_ok(graph_updated_file)

@schedule(job=daily_update_job, cron_schedule="0 0 * * *", default_status=DefaultScheduleStatus.RUNNING)
def daily_update_schedule(context):
    return RunRequest(run_key=context.scheduled_execution_time.strftime("%Y%m%d"))
