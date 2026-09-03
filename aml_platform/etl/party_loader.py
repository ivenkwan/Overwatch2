import os
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aml-party-projection")

# ==========================================
# PHASE 6: PARTY / UBO GRAPH PROJECTION
# ==========================================
# Projects the relational party dimension (init-scripts/06-party-ubo-model.sql)
# into the aml_network graph so the SCN_CROSS_RAIL_LAYER_01 rule can traverse
# instrument -> OWNED_BY -> party -> UBO_OF* -> ubo to establish
# "same beneficial owner" across rails.
#
# Idempotent (MERGE). Run after 06-party-ubo-model.sql and after
# graph_loader.py has promoted the instrument Entities (accounts/wallets).


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aml_platform"),
        user=os.getenv("DB_USER", "aml_admin"),
        password=os.getenv("DB_PASSWORD", "aml_secure_api_password"),
    )


def _esc(value):
    """Escape a value for an openCypher single-quoted string literal."""
    if value is None:
        return ""
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _cypher(cur, statement):
    """Execute a ``SELECT * FROM cypher('aml_network', $$ ... $$) AS (a agtype);`` block."""
    cur.execute(statement)


def _merge_party(cur, party_id, party_type, risk_rating, jurisdiction):
    _cypher(cur, (
        "SELECT * FROM cypher('aml_network', $$\n"
        f"    MERGE (p:Party {{id: '{_esc(party_id)}', "
        f"type: '{_esc(party_type)}', "
        f"risk_rating: '{_esc(risk_rating)}', "
        f"jurisdiction: '{_esc(jurisdiction)}'}})\n"
        "$$) as (a agtype);\n"
    ))


def _merge_owned_by(cur, instrument_id, party_id):
    # Link the instrument Entity to its controlling Party. Entity must already
    # exist (created by graph_loader); if not, the MATCH silently no-ops.
    _cypher(cur, (
        "SELECT * FROM cypher('aml_network', $$\n"
        f"    MATCH (e:Entity {{id: '{_esc(instrument_id)}'}}), "
        f"(p:Party {{id: '{_esc(party_id)}'}})\n"
        "    MERGE (e)-[:OWNED_BY]->(p)\n"
        "$$) as (a agtype);\n"
    ))


def _merge_ubo_of(cur, subject_party_id, ubo_party_id, ownership_pct):
    if ownership_pct is not None:
        edge = f"-[:UBO_OF{{ownership_pct: {float(ownership_pct)}}}]->"
    else:
        edge = "-[:UBO_OF]->"
    _cypher(cur, (
        "SELECT * FROM cypher('aml_network', $$\n"
        f"    MATCH (s:Party {{id: '{_esc(subject_party_id)}'}}), "
        f"(u:Party {{id: '{_esc(ubo_party_id)}'}})\n"
        f"    MERGE (s){edge}(u)\n"
        "$$) as (a agtype);\n"
    ))


def run_party_projection():
    logger.info("=== Starting Party/UBO Graph Projection ===")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")

        # 1. Party vertices
        cur.execute("SELECT party_id, party_type, risk_rating, jurisdiction FROM ag_catalog.party;")
        parties = cur.fetchall()
        for party_id, ptype, risk, juris in parties:
            _merge_party(cur, party_id, ptype, risk, juris)
        logger.info("Projected %d Party vertices.", len(parties))

        # 2. OWNED_BY: instrument Entity -> Party (effective mappings only)
        cur.execute(
            "SELECT instrument_id, party_id FROM ag_catalog.party_instrument "
            "WHERE valid_to IS NULL OR valid_to > CURRENT_TIMESTAMP;"
        )
        owned = cur.fetchall()
        for instrument_id, party_id in owned:
            _merge_owned_by(cur, instrument_id, party_id)
        logger.info("Projected %d OWNED_BY edges.", len(owned))

        # 3. UBO_OF: Party -> Party
        cur.execute("SELECT subject_party_id, ubo_party_id, ownership_pct FROM ag_catalog.party_ubo;")
        ubos = cur.fetchall()
        for subject, ubo, pct in ubos:
            _merge_ubo_of(cur, subject, ubo, pct)
        logger.info("Projected %d UBO_OF edges.", len(ubos))

        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info("=== Party/UBO Projection Complete ===")


if __name__ == "__main__":
    run_party_projection()
