-- ==========================================
-- PHASE 3b: SERVER-SIDE GRAPH PROMOTION (parameterized)
-- ==========================================
-- Why: Apache AGE requires the Cypher body inside a dollar-quoted string,
-- so client-side bind parameters can never reach inside $$...$$. Building
-- the query text in Python (f-strings) is therefore the classic injection
-- vector this pipeline had. This function moves the interpolation
-- server-side: Python calls it with typed %s bind parameters only, and the
-- arguments here are function parameters — values, never query structure.
--
-- Idempotent: MERGE on both endpoints, CREATE only the Transfer edge.

LOAD 'age';
SET search_path = ag_catalog, "$user", public;

CREATE OR REPLACE FUNCTION ag_catalog.promote_transfer(
    p_ref        text,
    p_src        text,
    p_dst        text,
    p_system     text,
    p_src_super  boolean,
    p_dst_super  boolean,
    p_amount     numeric,
    p_ts_epoch   bigint,
    p_timestamp  text,
    p_asset      text
) RETURNS void AS $fn$
DECLARE
    src_lbl text := CASE WHEN p_src_super THEN 'SuperNode' ELSE 'Entity' END;
    dst_lbl text := CASE WHEN p_dst_super THEN 'SuperNode' ELSE 'Entity' END;
    asset_prop text := CASE WHEN p_asset IS NULL THEN ''
                            ELSE ', asset: ' || quote_literal(p_asset) END;
BEGIN
    EXECUTE format(
        'SELECT * FROM ag_catalog.cypher(''aml_network'', $$ '
        '    MERGE (s:%s {id: %s, system: %s}) '
        '    MERGE (r:%s {id: %s, system: %s}) '
        '    CREATE (s)-[t:Transfer { '
        '        amount_usd: %s, '
        '        timestamp: %s, '
        '        ts: %s%s, '
        '        ref_id: %s '
        '    }]->(r) '
        ' $$) as (v agtype);',
        src_lbl, quote_literal(p_src), quote_literal(p_system),
        dst_lbl, quote_literal(p_dst), quote_literal(p_system),
        p_amount, quote_literal(p_timestamp), p_ts_epoch, asset_prop,
        quote_literal(p_ref)
    );
END
$fn$ LANGUAGE plpgsql;
