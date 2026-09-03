import os
import logging
import re

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aml-graph-builder")

# Values that reach the graph must pass this strict allowlist (mirrors the
# backend graph_service hardening): ids, hashes, networks, assets, ISO
# timestamps. The promotion query itself is executed server-side via
# ag_catalog.promote_transfer(...) with typed bind parameters — Python never
# builds query text from data.
_GRAPH_TOKEN = re.compile(r"^[A-Za-z0-9._:+@-]{1,64}$")


def _valid_token(value) -> bool:
    return value is not None and _GRAPH_TOKEN.match(str(value)) is not None


def _valid_optional(value) -> bool:
    return value is None or _valid_token(value)

# ==========================================
# PHASE 3: GRAPH CONSTRUCTION PIPELINE
# ==========================================

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="aml_platform",
        user="aml_admin",
        password=os.environ["DB_PASSWORD"]
    )

def get_super_nodes(cur):
    """
    Fetches the super-nodes from the relational database.
    """
    cur.execute("SELECT node_id FROM ag_catalog.super_nodes;")
    return [row[0] for row in cur.fetchall()]

def _promote_rows(cur, records, super_nodes, rail, has_asset):
    """Promote staging rows via the parameterized server-side function.

    Rows failing allowlist validation (a poisoned feed) are skipped and
    logged rather than promoted.
    """
    promoted = skipped = 0
    for record in records:
        if has_asset:
            ref, src, dst, amount, system, asset, timestamp, ts_epoch = record
        else:
            ref, src, dst, amount, timestamp, ts_epoch = record
            system, asset = rail, None

        # Normalize datetimes to ISO-8601 (compact, space-free) before the
        # allowlist check — str(datetime) contains spaces and would fail.
        if timestamp is not None and hasattr(timestamp, "isoformat"):
            timestamp = timestamp.isoformat()

        if not (_valid_token(ref) and _valid_token(src) and _valid_token(dst)
                and _valid_token(system) and _valid_optional(asset)
                and _valid_optional(timestamp)):
            skipped += 1
            logger.warning("Skipping %s row failing identifier allowlist: %s", rail, ref)
            continue
        try:
            amount = float(amount)
            ts_epoch = int(ts_epoch)
        except (TypeError, ValueError):
            skipped += 1
            logger.warning("Skipping %s row with non-numeric amount/ts: %s", rail, ref)
            continue

        cur.execute("SELECT ag_catalog.promote_transfer(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (str(ref), str(src), str(dst), str(system),
                     src in super_nodes, dst in super_nodes,
                     amount, ts_epoch, str(timestamp) if timestamp else None,
                     str(asset) if asset else None))
        promoted += 1

    if skipped:
        logger.warning("%s promotion skipped %d row(s) failing allowlist validation", rail, skipped)
    return promoted, skipped

def promote_fiat_to_graph(cur, super_nodes):
    """
    Translates tabular SCREENED fiat elements into graph Transfer edges
    (parameterized server-side promotion).
    """
    cur.execute("SELECT transfer_id, sender_account, receiver_account, amount_usd, transaction_timestamp, COALESCE(EXTRACT(EPOCH FROM transaction_timestamp)::bigint, 0) AS ts_epoch FROM ag_catalog.staging_fiat_raw WHERE status = 'SCREENED';")
    records = cur.fetchall()
    promoted, _ = _promote_rows(cur, records, super_nodes, "FIAT", has_asset=False)

    cur.execute("UPDATE ag_catalog.staging_fiat_raw SET status = 'GRAPHED' WHERE status = 'SCREENED';")
    logger.info("Promoted %d FIAT records to graph.", promoted)

def promote_crypto_to_graph(cur, super_nodes):
    """
    Translates tabular SCREENED crypto elements into graph Transfer edges
    (parameterized server-side promotion).
    """
    cur.execute("SELECT tx_hash, sender_wallet, receiver_wallet, volume_usd, network, asset_id, transaction_timestamp, COALESCE(EXTRACT(EPOCH FROM transaction_timestamp)::bigint, 0) AS ts_epoch FROM ag_catalog.staging_crypto_raw WHERE status = 'SCREENED';")
    records = cur.fetchall()
    promoted, _ = _promote_rows(cur, records, super_nodes, None, has_asset=True)

    cur.execute("UPDATE ag_catalog.staging_crypto_raw SET status = 'GRAPHED' WHERE status = 'SCREENED';")
    logger.info("Promoted %d CRYPTO records to graph.", promoted)

def run_graph_promotion():
    logger.info("=== Starting Graph Construction Pipeline ===")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Load AGE extension and set search path
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")

        super_nodes = get_super_nodes(cur)
        promote_fiat_to_graph(cur, super_nodes)
        promote_crypto_to_graph(cur, super_nodes)

        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info("=== Graph Construction Completed ===")

if __name__ == "__main__":
    run_graph_promotion()
