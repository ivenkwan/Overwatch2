import csv
import random
import os
from datetime import datetime, timedelta

def generate_csv():
    headers = ["customer num", "txn_date", "txn_ref_no", "Counterparties", "txn_country", "txn_currency", "txn currency_amount", "txn_amount_in_hkd", "cdi_code", "Txn Type"]
    data = []
    
    ref_no = 1
    base_date = datetime(2026, 6, 1) # Set to yesterday so they align with our demo alerts
    
    # 1. Complex Circular Chain (C_CIRC_1 -> C_CIRC_2 -> ... -> C_CIRC_8 -> C_CIRC_1)
    circ_nodes = [f"C_CIRC_{i}" for i in range(1, 9)]
    for i in range(len(circ_nodes)):
        src = circ_nodes[i]
        dst = circ_nodes[(i + 1) % len(circ_nodes)]
        amount = 75000 + random.randint(-1000, 1000)
        # Debit from src (transfer to dst)
        data.append([src, (base_date + timedelta(minutes=i*10)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, dst, "HKG", "HKD", str(amount), str(amount), "D", "TRANSFER_P2P"])
        ref_no += 1
        # Credit to dst (received from src)
        data.append([dst, (base_date + timedelta(minutes=i*10)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, src, "HKG", "HKD", str(amount), str(amount), "C", "TRANSFER_P2P"])
        ref_no += 1

    # 2. Layered Money Laundering Hub-and-Spoke (Smurfing/Consolidation)
    # 30 Smurfs -> 5 Layering -> 2 Hubs -> 3 External
    smurfs = [f"C_SMURF_{i}" for i in range(1, 31)]
    layers = [f"C_LAYER_{i}" for i in range(1, 6)]
    hubs = [f"C_HUB_{i}" for i in range(1, 3)]
    externals = [f"CP_OUT_{i}" for i in range(1, 4)]
    
    # Smurfs transfer below threshold (e.g. 9500) to Layering accounts
    for smurf in smurfs:
        layer = random.choice(layers)
        amount = 9500 + random.randint(-400, 400)
        data.append([smurf, (base_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, layer, "HKG", "HKD", str(amount), str(amount), "D", "TRANSFER_P2P"])
        ref_no += 1
        data.append([layer, (base_date + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, smurf, "HKG", "HKD", str(amount), str(amount), "C", "TRANSFER_P2P"])
        ref_no += 1
        
    # Layering accounts transfer to Hubs
    for layer in layers:
        for hub in hubs:
            amount = 45000 + random.randint(-2000, 2000)
            data.append([layer, (base_date + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, hub, "HKG", "HKD", str(amount), str(amount), "D", "TRANSFER_P2P"])
            ref_no += 1
            data.append([hub, (base_date + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, layer, "HKG", "HKD", str(amount), str(amount), "C", "TRANSFER_P2P"])
            ref_no += 1
            
    # Hubs transfer to Externals (Merchants/Foreign counterparties)
    for hub in hubs:
        for ext in externals:
            amount = 120000 + random.randint(-5000, 5000)
            data.append([hub, (base_date + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, ext, "HKG", "HKD", str(amount), str(amount), "D", "TRANSFER_P2P"])
            ref_no += 1
            data.append([ext, (base_date + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, hub, "HKG", "HKD", str(amount), str(amount), "C", "TRANSFER_P2P"])
            ref_no += 1

    # 3. Dense Bipartite/Clique Network (15 tightly connected nodes)
    clique_nodes = [f"C_CLIQUE_{i}" for i in range(1, 16)]
    # Create multiple transactions between random pairs in the clique
    for _ in range(80):
        src, dst = random.sample(clique_nodes, 2)
        amount = random.randint(1000, 15000)
        t_offset = random.randint(0, 1440) # random minutes over the day
        data.append([src, (base_date + timedelta(minutes=t_offset)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, dst, "HKG", "HKD", str(amount), str(amount), "D", "TRANSFER_P2P"])
        ref_no += 1
        data.append([dst, (base_date + timedelta(minutes=t_offset)).strftime("%Y-%m-%d %H:%M:%S"), ref_no, src, "HKG", "HKD", str(amount), str(amount), "C", "TRANSFER_P2P"])
        ref_no += 1

    # 4. Standard normal transactions noise (200 records)
    for i in range(200):
        sender = f"C_NORM_{1000 + i}"
        receiver = f"C_NORM_{2000 + i}"
        amount = random.randint(50, 5000)
        data.append([sender, base_date.strftime("%Y-%m-%d %H:%M:%S"), ref_no, receiver, "HKG", "HKD", str(amount), str(amount), "D", "TRANSFER_P2P"])
        ref_no += 1
        data.append([receiver, base_date.strftime("%Y-%m-%d %H:%M:%S"), ref_no, sender, "HKG", "HKD", str(amount), str(amount), "C", "TRANSFER_P2P"])
        ref_no += 1

    # Ensure output directory exists
    today_str = datetime.now().strftime("%Y%m%d")
    output_dir = "d:\\DEVHOME\\Overwatch\\input_data"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{today_str}_CUST_TNG.csv")
    
    # Overwrite any existing file
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        
    print(f"Successfully generated {file_path} with {len(data)} transactions.")

if __name__ == "__main__":
    generate_csv()
