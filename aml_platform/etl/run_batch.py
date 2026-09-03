import os
import json
import logging
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aml-etl-batch")

# ==========================================
# PHASE 2: NORMALIZATION SCRIPTS
# ==========================================

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="aml_platform",
        user="aml_admin",
        password=os.getenv("DB_PASSWORD", "aml_secure_api_password")
    )

def normalize_fiat_swift(raw_swift_json):
    """
    Simulates parsing messy TradFi SWIFT payloads into the relational
    staging_fiat_raw DDL schema format.
    """
    logger.info("Normalizing Fiat SWIFT batch...")
    normalized_records = []
    
    for msg in raw_swift_json:
        try:
            record = (
                msg["InstructionID"],
                msg["OrderingCustomer"]["Account"],
                msg["OrderingCustomer"]["BIC"],
                msg["BeneficiaryCustomer"]["Account"],
                msg["BeneficiaryCustomer"]["BIC"],
                float(msg["AmountInfo"]["SettlementAmount"]), 
                msg["ValueDate"],
                "PENDING"
            )
            normalized_records.append(record)
        except KeyError as e:
            logger.error(f"Missing crucial field for fiat record. Route to DLQ: {e}")
            
    return normalized_records

def normalize_crypto_txn(raw_crypto_json):
    """
    Simulates parsing Web3/Crypto block explorer API or Node RPC data (e.g. UTXO/Account)
    into the staging_crypto_raw DDL schema format.
    """
    logger.info("Normalizing Crypto On-Chain batch...")
    normalized_records = []
    
    for tx in raw_crypto_json:
        try:
            record = (
                tx["hash"],
                tx["from"],
                tx["to"],
                tx["tokenSymbol"] if "tokenSymbol" in tx else "NATIVE",
                float(tx["value"]) / (10**18), 
                float(tx["historical_usd_value"]), 
                tx.get("network", "ETHEREUM"),
                datetime.fromtimestamp(int(tx["timeStamp"])).isoformat(),
                "PENDING"
            )
            normalized_records.append(record)
        except KeyError as e:
            logger.error(f"Missing crucial field for crypto record. Route to DLQ: {e}")
            
    return normalized_records

# ==========================================
# PHASE 2: ORCHESTRATOR SCAFFOLD
# ==========================================

def run_t1_batch_job():
    logger.info("=== Starting T+1 AML Batch Job ===")
    
    # 1. Mock Data (to actually execute)
    mock_fiat = [
        {
            "InstructionID": "SWIFT-FIAT-1001",
            "OrderingCustomer": {"Account": "ACC_SUSPECT_01", "BIC": "BANKUS33"},
            "BeneficiaryCustomer": {"Account": "ACC_02", "BIC": "BANKCH22"},
            "AmountInfo": {"SettlementAmount": "15000.00"},
            "ValueDate": datetime.now().isoformat()
        },
        {
            "InstructionID": "SWIFT-FIAT-1002",
            "OrderingCustomer": {"Account": "ACC_02", "BIC": "BANKCH22"},
            "BeneficiaryCustomer": {"Account": "ACC_SUSPECT_01", "BIC": "BANKUS33"},
            "AmountInfo": {"SettlementAmount": "14000.00"},
            "ValueDate": datetime.now().isoformat()
        }
    ]
    mock_crypto = [
        {
            "hash": "TX_S1",
            "from": "USER_A", "to": "USER_B",
            "tokenSymbol": "USDT", "value": str(4000 * 10**18), "historical_usd_value": "4000.00",
            "network": "ETHEREUM", "timeStamp": str(int(datetime.now().timestamp()))
        },
        {
            "hash": "TX_S2",
            "from": "USER_A", "to": "USER_B",
            "tokenSymbol": "USDT", "value": str(4000 * 10**18), "historical_usd_value": "4000.00",
            "network": "ETHEREUM", "timeStamp": str(int(datetime.now().timestamp()))
        },
        {
            "hash": "TX_S3",
            "from": "USER_A", "to": "USER_B",
            "tokenSymbol": "USDT", "value": str(4000 * 10**18), "historical_usd_value": "4000.00",
            "network": "ETHEREUM", "timeStamp": str(int(datetime.now().timestamp()))
        }
    ]


    # 2. Normalize
    fiat_staged = normalize_fiat_swift(mock_fiat)
    crypto_staged = normalize_crypto_txn(mock_crypto)
    
    # 3. Persist
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        execute_values(cur, 
            "INSERT INTO ag_catalog.staging_fiat_raw (transfer_id, sender_account, sender_bank_routing, receiver_account, receiver_bank_routing, amount_usd, transaction_timestamp, status) VALUES %s ON CONFLICT DO NOTHING",
            fiat_staged)
        execute_values(cur, 
            "INSERT INTO ag_catalog.staging_crypto_raw (tx_hash, sender_wallet, receiver_wallet, asset_id, volume_native, volume_usd, network, transaction_timestamp, status) VALUES %s ON CONFLICT DO NOTHING",
            crypto_staged)
        
        # 4. Trigger Regulatory Gate
        logger.info("Evaluating OFAC Sanctions...")
        cur.execute("CALL public.sp_screen_ofac();")
        
        conn.commit()
        logger.info("Staged and Screened data.")
    finally:
        cur.close()
        conn.close()
    
    logger.info("=== T+1 AML Batch Job Completed ===")

if __name__ == "__main__":
    run_t1_batch_job()

