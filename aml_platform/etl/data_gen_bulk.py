import random
import uuid
from datetime import datetime, timedelta

def generate_bulk_data(count=20000):
    sql_statements = []
    
    # 1. Generate Peeling Chains (approx 30% of data)
    for i in range(count // 3):
        chain_id = str(uuid.uuid4())[:8]
        source = f"SOURCE_{chain_id}"
        amount = random.randint(50000, 200000)
        
        # 4-6 hop peel
        for hop in range(random.randint(4, 6)):
            peel_id = f"PEEL_{chain_id}_{hop}"
            change_id = f"CHANGE_{chain_id}_{hop}"
            target_id = f"TARGET_{chain_id}_{hop}"
            
            peel_amt = amount * random.uniform(0.05, 0.25)
            change_amt = amount - peel_amt
            
            # Peel Tx
            sql_statements.append(
                f"INSERT INTO staging_crypto_raw (tx_hash, sender_wallet, receiver_wallet, asset_id, volume_native, volume_usd, network, transaction_timestamp) "
                f"VALUES ('TX_PEEL_{uuid.uuid4().hex[:10]}', '{source}', '{target_id}', 'USDT', {peel_amt:.2f}, {peel_amt:.2f}, 'ETHEREUM', NOW() - INTERVAL '{hop} hours');"
            )
            # Change Tx
            sql_statements.append(
                f"INSERT INTO staging_crypto_raw (tx_hash, sender_wallet, receiver_wallet, asset_id, volume_native, volume_usd, network, transaction_timestamp) "
                f"VALUES ('TX_CHANGE_{uuid.uuid4().hex[:10]}', '{source}', '{change_id}', 'USDT', {change_amt:.2f}, {change_amt:.2f}, 'ETHEREUM', NOW() - INTERVAL '{hop} hours' + INTERVAL '30 minutes');"
            )
            source = change_id # Next hop starts from change address
            amount = change_amt
            if amount < 1000: break

    # 2. Generate High-Velocity Layering (approx 30% of data)
    for i in range(count // 30): # Each cluster has ~10-20 tx
        cluster_id = str(uuid.uuid4())[:8]
        source = f"SRC_LAYER_{cluster_id}"
        sink = f"SINK_LAYER_{cluster_id}"
        mules = [f"MULE_{cluster_id}_{j}" for j in range(random.randint(3, 8))]
        
        base_amt = random.randint(10000, 550000)
        
        for mule in mules:
            # Fan-out
            sql_statements.append(
                f"INSERT INTO staging_crypto_raw (tx_hash, sender_wallet, receiver_wallet, asset_id, volume_native, volume_usd, network, transaction_timestamp) "
                f"VALUES ('TX_FO_{uuid.uuid4().hex[:10]}', '{source}', '{mule}', 'USDC', {base_amt:.2f}, {base_amt:.2f}, 'ETHEREUM', NOW() - INTERVAL '50 minutes');"
            )
            # Fan-in
            sink_amt = base_amt * 0.99 # 1% fee peel
            sql_statements.append(
                f"INSERT INTO staging_crypto_raw (tx_hash, sender_wallet, receiver_wallet, asset_id, volume_native, volume_usd, network, transaction_timestamp) "
                f"VALUES ('TX_FI_{uuid.uuid4().hex[:10]}', '{mule}', '{sink}', 'USDC', {sink_amt:.2f}, {sink_amt:.2f}, 'ETHEREUM', NOW() - INTERVAL '10 minutes');"
            )

    # 3. Generate Random Noise (remaining data)
    for i in range(len(sql_statements), count):
        sql_statements.append(
            f"INSERT INTO staging_crypto_raw (tx_hash, sender_wallet, receiver_wallet, asset_id, volume_native, volume_usd, network, transaction_timestamp) "
            f"VALUES ('TX_NOISE_{uuid.uuid4().hex[:10]}', 'WAL_{random.randint(1000, 9999)}', 'WAL_{random.randint(1000, 9999)}', 'ETH', {random.uniform(0.1, 5):.4f}, {random.randint(100, 15000):.2f}, 'ETHEREUM', NOW() - INTERVAL '{random.randint(1, 48)} hours');"
        )

    with open('bulk_synthetic_data.sql', 'w') as f:
        f.write("\n".join(sql_statements[:count]))

import sys

if __name__ == "__main__":
    count = 20000
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    generate_bulk_data(count)
    print(f"Generated {count} rows in bulk_synthetic_data.sql")
