import sys
import os
import subprocess
import logging
import psycopg2
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aml-reload-demo")

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
        # command can be a string or list. If it's a list, use it directly.
        cmd = ["python"] + command if isinstance(command, list) else ["python", command]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.info(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        logger.error(f"Error in {description}: {e.stderr}")
        raise

def drop_and_recreate_data():
    logger.info("--- Cleaning up previous Demo Data ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute("SET search_path = ag_catalog, public;")
        
        # 1. Truncate staging and alerts
        logger.info("Truncating relational tables...")
        cur.execute("TRUNCATE TABLE staging_crypto_raw CASCADE;")
        cur.execute("TRUNCATE TABLE staging_fiat_raw CASCADE;")
        cur.execute("TRUNCATE TABLE alerts CASCADE;")
        
        # 2. Reset the Graph database
        logger.info("Dropping and recreating tap_and_go_network graph...")
        # To reset age graph, we must drop the graph and create it again 
        # (Assuming the graph is named tap_and_go_network from init scripts)
        cur.execute("SELECT drop_graph('tap_and_go_network', true);")
        cur.execute("SELECT create_graph('tap_and_go_network');")
        
        conn.commit()
    except Exception as e:
        # Ignore errors if graph didn't exist or table dropped
        logger.warning(f"Note during cleanup: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python reload_env_and_demo.py <RECORD_COUNT>")
        print("Example: python reload_env_and_demo.py 9000")
        record_count = 9000
    else:
        record_count = int(sys.argv[1])

    logger.info(f"🚀 Starting Environment Reload & Demo Automation Pipeline with {record_count} Records...")
    
    # 1. Clean existing data
    drop_and_recreate_data()
    
    # Ensure tables exist
    run_command("run_demo_demo.py", "Ensuring Schema Exists (via demo runner initialization)")
    
    # 2. Generate new bulk data
    run_command(["data_gen_bulk.py", str(record_count)], f"Generating {record_count} rows of synthetic data")
    
    # 3. Load Bulk Data
    logger.info("--- Loading Bulk SQL: bulk_synthetic_data.sql ---")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute("SET search_path = ag_catalog, public;")
        with open("bulk_synthetic_data.sql", 'r') as f:
            cur.execute(f.read())
        conn.commit()
        logger.info("Bulk SQL load successful.")
    except Exception as e:
        logger.error(f"Error loading SQL: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    
    # 4. Promote to Graph (ETL)
    run_command("run_batch.py", "Running ETL: Relational -> Graph Promotion")
    
    # 5. Trigger Rule Engine (Alerting)
    run_command("rule_engine.py", "Executing OpenCypher Rule Engine")
    
    logger.info("✅ Demo Automation Complete. Launching Dashboard visualization...")
    
    # Launch browser to see the dashboard
    if os.name == 'nt':
        os.system('start http://localhost:3000')
    elif os.name == 'posix':
        os.system('open http://localhost:3000')

if __name__ == "__main__":
    main()
