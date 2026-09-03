import psycopg2
import os
import traceback

POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://postgres:password@age_db:5432/age_prod_01")
try:
    conn = psycopg2.connect(POSTGRES_URI)
    cursor = conn.cursor()
    cursor.execute("SET search_path = ag_catalog, \"$user\", public;")

    sql_script = """
    DO $$
    DECLARE
        t record;
    BEGIN
        FOR t IN SELECT txn_hash, customer_num, counterparty_id, cdi_code, txn_amount_in_hkd, is_merchant 
                 FROM core.transactions txn
                 JOIN core.counterparties c ON txn.counterparty_id = c.counterparty_id LOOP
            
            IF t.cdi_code = 'D' THEN
                IF t.is_merchant THEN
                    EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ 
                        MATCH (src:Customer {id: ''%s''}), (dst:Merchant {id: ''%s''})
                        MERGE (src)-[e:PAID {txn_hash: ''%s'', amount: %s}]->(dst)
                    $cypher$) AS (a agtype);', t.customer_num, t.counterparty_id, t.txn_hash, t.txn_amount_in_hkd);
                ELSE
                    EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ 
                        MATCH (src:Customer {id: ''%s''}), (dst:Counterparty {id: ''%s''})
                        MERGE (src)-[e:TRANSFERRED {txn_hash: ''%s'', amount: %s}]->(dst)
                    $cypher$) AS (a agtype);', t.customer_num, t.counterparty_id, t.txn_hash, t.txn_amount_in_hkd);
                END IF;
            ELSE
                EXECUTE format('SELECT * FROM cypher(''tap_and_go_network'', $cypher$ 
                    MATCH (src:Counterparty {id: ''%s''}), (dst:Customer {id: ''%s''})
                    MERGE (src)-[e:TRANSFERRED {txn_hash: ''%s'', amount: %s}]->(dst)
                $cypher$) AS (a agtype);', t.counterparty_id, t.customer_num, t.txn_hash, t.txn_amount_in_hkd);
            END IF;
        END LOOP;
    END
    $$;
    """
    cursor.execute(sql_script)
    conn.commit()
    print("SUCCESS edges")
except Exception as e:
    print("FAILED:", str(e))
    traceback.print_exc()
