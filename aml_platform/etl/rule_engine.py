import os
import logging
import json
import psycopg2

from scenarios import SCENARIOS, DEFAULT_PARAMS, RULE_VERSION, render_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aml-cypher-rule-engine")

# ==========================================
# PHASE 4: OPENCYPHER RULE ENGINE (v5 scenario registry)
# ==========================================
# Iterates the scenario registry (scenarios.py), injecting tunable params
# into each Cypher query and sinking hits into the v5-enriched `alerts`
# table. Thresholds are overridable via environment variables of the same
# name (e.g. SMURFING_TOTAL_USD=8000) so operators can tune without code
# edits — see scenarios.DEFAULT_PARAMS for the full set.


def _coerce(raw, sample):
    """Coerce an env-string to match the type of the default value."""
    if isinstance(sample, bool):
        return raw.lower() in ("1", "true", "yes")
    if isinstance(sample, int):
        return int(raw)
    if isinstance(sample, float):
        return float(raw)
    return raw


def resolve_params():
    """DEFAULT_PARAMS overridden by any matching environment variable."""
    params = dict(DEFAULT_PARAMS)
    for key, default in DEFAULT_PARAMS.items():
        env_val = os.environ.get(key)
        if env_val is not None and env_val.strip() != "":
            try:
                params[key] = _coerce(env_val.strip(), default)
            except (ValueError, TypeError):
                logger.warning("Ignoring invalid env override %s=%r (expected %s)",
                               key, env_val, type(default).__name__)
    return params


def get_db_connection():
    # Production: Use Environment Variables
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aml_platform"),
        user=os.getenv("DB_USER", "aml_admin"),
        password=os.getenv("DB_PASSWORD", "aml_secure_api_password"),
    )


def execute_rules_and_sink_alerts():
    logger.info("Starting OpenCypher Rule Engine evaluation (rule_version=%s, %d scenarios)...",
                RULE_VERSION, len(SCENARIOS))

    params = resolve_params()
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, public;")

        # Graph labels present in aml_network — used to gate scenarios that
        # depend on optional dimensions (e.g. Party/UBO for Cross-Rail).
        cur.execute("SELECT name FROM ag_catalog.ag_label;")
        graph_labels = {row[0] for row in cur.fetchall()}

        for scenario in SCENARIOS:
            required = scenario.get("requires_labels") or ()
            missing = [lbl for lbl in required if lbl not in graph_labels]
            if missing:
                logger.info(
                    "Skipping %s [%s] — graph labels not present: %s "
                    "(apply the matching init script + loader, e.g. "
                    "06-party-ubo-model.sql + party_loader.py)",
                    scenario["name"], scenario["code"], missing,
                )
                continue

            query = render_query(scenario, params)
            logger.info("Executing Rule Strategy: %s [%s] (%s/%s)",
                        scenario["name"], scenario["code"], scenario["rail"], scenario["mode"])
            try:
                cur.execute(query)
                hits = cur.fetchall()

                if hits:
                    logger.warning("Engine fired %d alerts for %s", len(hits), scenario["name"])
                    for hit in hits:
                        entity_id = hit[0]
                        tx_hashes = hit[1]
                        # Evidentiary sink — records the stable v5 scenario identity.
                        cur.execute(
                            "INSERT INTO ag_catalog.alerts "
                            "(alert_type, scenario_code, scenario_category, rail, ml_typology, "
                            " severity, trigger_entity, related_transactions, rule_version) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                scenario["name"],
                                scenario["code"],
                                scenario["category"],
                                scenario["rail"],
                                scenario.get("ml_typology"),
                                scenario["severity"],
                                str(entity_id),
                                json.dumps(tx_hashes),
                                RULE_VERSION,
                            ),
                        )
            except Exception as e:
                logger.error("Rule %s failed: %s", scenario["name"], str(e))
                conn.rollback()  # Don't halt entire engine for one bad rule
                continue

        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info("Rule Engine evaluation complete.")


if __name__ == "__main__":
    execute_rules_and_sink_alerts()
