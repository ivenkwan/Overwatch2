import polars as pl
import hashlib
from dagster import asset, Config
import psycopg2
from psycopg2.extras import execute_values
import os

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://postgres:password@age_db:5432/age_prod_01")

class IngestConfig(Config):
    filepath: str = "/opt/dagster/input_data/sample_6_customers_TXN_202510.csv.csv"

@asset
def raw_ledger_data(config: IngestConfig) -> pl.DataFrame:
    """Reads the raw CSV file and performs basic column renaming and typing."""
    # Use localhost if running outside container for dev
    local_path = config.filepath if os.path.exists(config.filepath) else "input_data/sample_6_customers_TXN_202510.csv.csv"
    if not os.path.exists(local_path):
        # Fallback to absolute for container mount testing
        local_path = "z:\\GITHUB\\Overwatch\\input_data\\sample_6_customers_TXN_202510.csv.csv"
        
    df = pl.read_csv(local_path, infer_schema_length=10000, ignore_errors=True)
    df = df.rename({
        "customer num": "customer_num",
        "txn currency_amount": "txn_currency_amount",
        "Txn Type": "txn_type"
    })
    return df

@asset
def cleaned_ledger_data(raw_ledger_data: pl.DataFrame) -> pl.DataFrame:
    """Cleans counterparty names, hashes PKs, and formats columns."""
    df = raw_ledger_data.drop_nulls(subset=["txn_ref_no"])
    
    # Generate unique transaction hash (Idempotency key)
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
        if not s:
            return "UNKNOWN"
        s = str(s).strip()
        if s.startswith("PAY TO "):
            s = s.replace("PAY TO ", "")
        if s.startswith("PAY FROM "):
            s = s.replace("PAY FROM ", "")
        if s.startswith("(FOREIGN TXN FEE) "):
            s = s.replace("(FOREIGN TXN FEE) ", "")
        return s.strip()

    df = df.with_columns(
        pl.col("Counterparties").map_elements(clean_cp, return_dtype=pl.String).alias("counterparty_id")
    )
    
    return df

@asset
def load_relational_tables(cleaned_ledger_data: pl.DataFrame) -> None:
    """Loads normalized data into PostgreSQL core schema"""
    uri = POSTGRES_URI if not POSTGRES_URI.endswith("age_prod_01") else POSTGRES_URI.replace("age_db", "localhost")
    try:
        conn = psycopg2.connect(POSTGRES_URI)
    except psycopg2.OperationalError:
         # Fallback for local run
        conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/age_prod_01")
        
    cursor = conn.cursor()
    
    # 1. Load Customers
    customers = cleaned_ledger_data.select("customer_num").unique().to_dicts()
    execute_values(
        cursor,
        "INSERT INTO core.customers (customer_num) VALUES %s ON CONFLICT (customer_num) DO NOTHING",
        [(str(c["customer_num"]),) for c in customers]
    )
    
    # 2. Load Counterparties
    counterparties = cleaned_ledger_data.select(
        "counterparty_id",
        pl.col("txn_type").str.contains("MERCHANT").alias("is_merchant")
    ).unique("counterparty_id").to_dicts()
    
    execute_values(
        cursor,
        "INSERT INTO core.counterparties (counterparty_id, counterparty_name, is_merchant) VALUES %s ON CONFLICT (counterparty_id) DO NOTHING",
        [(str(c["counterparty_id"]), str(c["counterparty_id"]), bool(c["is_merchant"])) for c in counterparties]
    )
    
    # 3. Load Transactions
    txns = cleaned_ledger_data.to_dicts()
    
    def safe_float(v):
        try:
            return float(v)
        except:
            return 0.0

    execute_values(
        cursor,
        """INSERT INTO core.transactions 
        (txn_hash, customer_num, counterparty_id, txn_date, txn_ref_no, txn_country, txn_currency, txn_currency_amount, txn_amount_in_hkd, cdi_code, txn_type, source_filename)
        VALUES %s ON CONFLICT (txn_hash) DO NOTHING""",
        [(
            str(t["txn_hash"]), str(t["customer_num"]), str(t["counterparty_id"]), str(t["txn_date"]), str(t["txn_ref_no"]),
            str(t["txn_country"]), str(t["txn_currency"]), safe_float(t["txn_currency_amount"]), safe_float(t["txn_amount_in_hkd"]),
            str(t["cdi_code"]), str(t["txn_type"]), "sample_6_customers_TXN_202510.csv.csv"
        ) for t in txns]
    )
    
    conn.commit()
    cursor.close()
    conn.close()
