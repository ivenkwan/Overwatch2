from dagster import asset
import psycopg2
import os

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://postgres:password@age_db:5432/age_prod_01")

@asset(deps=["load_relational_tables"])
def update_age_graph() -> None:
    """Projects relational PostgreSQL tables into Apache AGE Graph."""
    try:
        conn = psycopg2.connect(POSTGRES_URI)
    except psycopg2.OperationalError:
         # Fallback for local run
        conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/age_prod_01")
        
    cursor = conn.cursor()

    cursor.execute("SET search_path = ag_catalog, \"$user\", public;")
    
    # Execute a Pl/PgSql DO block to iterate over new relational records and map them to AGE graph.
    # We MERGE the Nodes and the Edges to ensure idempotency.
    
    sql_script = """
    DO $$
    DECLARE
        c record;
        cp record;
        t record;
    BEGIN
        -- 1. Create Customer Nodes
        FOR c IN SELECT customer_num FROM core.customers LOOP
            EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ 
                MERGE (n:Customer {id: ''%s''}) 
            $cypher$) AS (a agtype);', c.customer_num);
        END LOOP;

        -- 2. Create Counterparty/Merchant Nodes
        FOR cp IN SELECT counterparty_id, is_merchant FROM core.counterparties LOOP
            IF cp.is_merchant THEN
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ 
                    MERGE (m:Merchant {id: ''%s''}) 
                $cypher$) AS (a agtype);', cp.counterparty_id);
            ELSE
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ 
                    MERGE (n:Counterparty {id: ''%s''}) 
                $cypher$) AS (a agtype);', cp.counterparty_id);
            END IF;
        END LOOP;
        
        -- 3. Create Transaction Edges
        FOR t IN SELECT txn.txn_hash, txn.customer_num, txn.counterparty_id, txn.cdi_code, txn.txn_amount_in_hkd, cp_tab.is_merchant AS is_merchant, COALESCE(EXTRACT(EPOCH FROM txn.txn_date)::bigint, 0) AS ts_epoch
                 FROM core.transactions txn
                 JOIN core.counterparties cp_tab ON txn.counterparty_id = cp_tab.counterparty_id LOOP

            IF t.cdi_code = 'D' THEN
                -- Debit: Customer -> Counterparty/Merchant
                IF t.is_merchant THEN
                    EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$
                        MATCH (src:Customer {id: ''%s''}), (dst:Merchant {id: ''%s''})
                        MERGE (src)-[e:PAID {txn_hash: ''%s'', amount: %s}]->(dst) SET e.ts = %s
                    $cypher$) AS (a agtype);', t.customer_num, t.counterparty_id, t.txn_hash, t.txn_amount_in_hkd, t.ts_epoch);
                ELSE
                    EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$
                        MATCH (src:Customer {id: ''%s''}), (dst:Counterparty {id: ''%s''})
                        MERGE (src)-[e:TRANSFERRED {txn_hash: ''%s'', amount: %s}]->(dst) SET e.ts = %s
                    $cypher$) AS (a agtype);', t.customer_num, t.counterparty_id, t.txn_hash, t.txn_amount_in_hkd, t.ts_epoch);
                END IF;
            ELSE
                -- Credit: Counterparty -> Customer
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$
                    MATCH (src:Counterparty {id: ''%s''}), (dst:Customer {id: ''%s''})
                    MERGE (src)-[e:TRANSFERRED {txn_hash: ''%s'', amount: %s}]->(dst) SET e.ts = %s
                $cypher$) AS (a agtype);', t.counterparty_id, t.customer_num, t.txn_hash, t.txn_amount_in_hkd, t.ts_epoch);
            END IF;
        END LOOP;
    END
    $$;
    """
    
    cursor.execute(sql_script)
    conn.commit()
    cursor.close()
    conn.close()
