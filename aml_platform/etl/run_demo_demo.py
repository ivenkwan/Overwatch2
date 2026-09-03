import os
import subprocess
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aml-demo-automation")

# Configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "aml_platform",
    "user": "aml_admin",
    "password": os.getenv("DB_PASSWORD", "aml_secure_api_password")
}

def run_command(command, description):
    logger.info(f"--- Running: {description} ---")
    try:
        result = subprocess.run(["python", command], check=True, capture_output=True, text=True)
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in {description}: {e.stderr}")
        raise

def load_sql_bulk(sql_file):
    logger.info(f"--- Loading Bulk SQL: {sql_file} ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        # Crucial: Set search_path so it finds tables in ag_catalog
        cur.execute("SET search_path = ag_catalog, public;")
        with open(sql_file, 'r') as f:
            sql = f.read()
            cur.execute(sql)
        conn.commit()
        logger.info("Bulk SQL load successful.")
    except Exception as e:
        logger.error(f"Error loading SQL: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def ensure_schema_exists():
    logger.info("--- Ensuring Schema Exists (init-scripts) ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        # Check in ag_catalog where the tables actually reside
        cur.execute("SELECT to_regclass('ag_catalog.staging_crypto_raw');")
        if cur.fetchone()[0] is None:
            logger.warning("Staging tables not found. Initializing from scripts...")
            script_paths = [
                "../init-scripts/01-init.sql",
                "../init-scripts/02-regulatory-procedures.sql",
                "../init-scripts/03-graph-schema.sql"
            ]
            for path in script_paths:
                logger.info(f"Executing: {path}")
                with open(path, 'r') as f:
                    content = f.read()
                    if content.strip():
                        try:
                            cur.execute(content)
                        except Exception as e:
                            # Handle common "already exists" errors during partial init
                            if "already exists" in str(e).lower():
                                logger.info(f"Notice: Some elements in {path} already exist. Continuing...")
                                conn.rollback()
                                continue
                            else:
                                logger.error(f"Failed to execute {path}: {str(e)}")
                                raise
            conn.commit()
            logger.info("Schema initialization complete.")
        else:
            logger.info("Schema already exists.")
    except Exception as e:
        logger.error(f"Error ensuring schema: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def main():
    logger.info("🚀 Starting Full AML Demo Automation Pipeline...")
    
    # 0. Ensure Schema
    ensure_schema_exists()
    
    # 1. Generate new bulk data
    run_command("data_gen_bulk.py", "Generating 1000 rows of synthetic data")
    
    # 2. Insert into Staging
    load_sql_bulk("bulk_synthetic_data.sql")
    
    # 3. Promote to Graph (ETL)
    run_command("run_batch.py", "Running ETL: Relational -> Graph Promotion")
    
    # 4. Trigger Rule Engine (Alerting)
    run_command("rule_engine.py", "Executing OpenCypher Rule Engine")
    
    logger.info("✅ Demo Automation Complete. Open the dashboard to see results.")

if __name__ == "__main__":
    main()
