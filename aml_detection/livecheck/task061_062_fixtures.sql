-- TASK-061/062 live fixtures for the aml_network graph (age_prod_01).
-- Idempotent: pre-cleans any prior LV* fixture nodes first.
-- Run: docker exec -i aml-age-db psql -U postgres -d age_prod_01 \
--        -c "LOAD 'age'; SET search_path = ag_catalog, \"\$user\", public;" \
--        -f aml_detection/livecheck/task061_062_fixtures.sql
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- pre-clean (idempotent re-runs)
SELECT * FROM cypher('aml_network', $$
  MATCH (n:Entity) WHERE n.id STARTS WITH 'LV' DETACH DELETE n
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (p:Party) WHERE p.id STARTS WITH 'LV' DETACH DELETE p
$$) as (v agtype);
DELETE FROM app.alerts WHERE payload->>'rule_version' = '2026.09-aml-detection-workbench';

-- peeling chain: 6 hops, ~0.90 value ratio each (fires SCN_PEEL_01)
SELECT * FROM cypher('aml_network', $$
  CREATE (n0:Entity {id: 'LVPEEL_A', system: 'FIAT'}),
         (n1:Entity {id: 'LVPEEL_M1', system: 'FIAT'}),
         (n2:Entity {id: 'LVPEEL_M2', system: 'FIAT'}),
         (n3:Entity {id: 'LVPEEL_M3', system: 'FIAT'}),
         (n4:Entity {id: 'LVPEEL_M4', system: 'FIAT'}),
         (n5:Entity {id: 'LVPEEL_M5', system: 'FIAT'}),
         (n6:Entity {id: 'LVPEEL_N', system: 'FIAT'})
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (a:Entity {id: 'LVPEEL_A'}), (b:Entity {id: 'LVPEEL_M1'}),
        (c:Entity {id: 'LVPEEL_M2'}), (d:Entity {id: 'LVPEEL_M3'}),
        (e:Entity {id: 'LVPEEL_M4'}), (f:Entity {id: 'LVPEEL_M5'}),
        (g:Entity {id: 'LVPEEL_N'})
  CREATE (a)-[:Transfer {amount_usd: 1000, ts: 1725000000, ref_id: 'LVPEEL_TX_1'}]->(b),
         (b)-[:Transfer {amount_usd: 900,  ts: 1725086400, ref_id: 'LVPEEL_TX_2'}]->(c),
         (c)-[:Transfer {amount_usd: 810,  ts: 1725172800, ref_id: 'LVPEEL_TX_3'}]->(d),
         (d)-[:Transfer {amount_usd: 730,  ts: 1725259200, ref_id: 'LVPEEL_TX_4'}]->(e),
         (e)-[:Transfer {amount_usd: 660,  ts: 1725345600, ref_id: 'LVPEEL_TX_5'}]->(f),
         (f)-[:Transfer {amount_usd: 590,  ts: 1725432000, ref_id: 'LVPEEL_TX_6'}]->(g)
$$) as (v agtype);

-- negative control: increasing values must NOT fire peeling
SELECT * FROM cypher('aml_network', $$
  CREATE (n0:Entity {id: 'LVPEELNEG_A', system: 'FIAT'}),
         (n1:Entity {id: 'LVPEELNEG_M1', system: 'FIAT'}),
         (n2:Entity {id: 'LVPEELNEG_M2', system: 'FIAT'}),
         (n3:Entity {id: 'LVPEELNEG_M3', system: 'FIAT'}),
         (n4:Entity {id: 'LVPEELNEG_N', system: 'FIAT'})
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (a:Entity {id: 'LVPEELNEG_A'}), (b:Entity {id: 'LVPEELNEG_M1'}),
        (c:Entity {id: 'LVPEELNEG_M2'}), (d:Entity {id: 'LVPEELNEG_M3'}),
        (e:Entity {id: 'LVPEELNEG_N'})
  CREATE (a)-[:Transfer {amount_usd: 100, ts: 1725000000, ref_id: 'LVPEELNEG_TX_1'}]->(b),
         (b)-[:Transfer {amount_usd: 200, ts: 1725086400, ref_id: 'LVPEELNEG_TX_2'}]->(c),
         (c)-[:Transfer {amount_usd: 300, ts: 1725172800, ref_id: 'LVPEELNEG_TX_3'}]->(d),
         (d)-[:Transfer {amount_usd: 400, ts: 1725259200, ref_id: 'LVPEELNEG_TX_4'}]->(e)
$$) as (v agtype);

-- rapid-layering chain: 4 hops, 1800s apart (fires SCN_LAYER_RAPID_01)
SELECT * FROM cypher('aml_network', $$
  CREATE (n0:Entity {id: 'LVRL_A', system: 'FIAT'}),
         (n1:Entity {id: 'LVRL_M1', system: 'FIAT'}),
         (n2:Entity {id: 'LVRL_M2', system: 'FIAT'}),
         (n3:Entity {id: 'LVRL_M3', system: 'FIAT'}),
         (n4:Entity {id: 'LVRL_N', system: 'FIAT'})
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (a:Entity {id: 'LVRL_A'}), (b:Entity {id: 'LVRL_M1'}),
        (c:Entity {id: 'LVRL_M2'}), (d:Entity {id: 'LVRL_M3'}),
        (e:Entity {id: 'LVRL_N'})
  CREATE (a)-[:Transfer {amount_usd: 500, ts: 1725000000, ref_id: 'LVRL_TX_1'}]->(b),
         (b)-[:Transfer {amount_usd: 500, ts: 1725001800, ref_id: 'LVRL_TX_2'}]->(c),
         (c)-[:Transfer {amount_usd: 500, ts: 1725003600, ref_id: 'LVRL_TX_3'}]->(d),
         (d)-[:Transfer {amount_usd: 500, ts: 1725005400, ref_id: 'LVRL_TX_4'}]->(e)
$$) as (v agtype);

-- negative control: 7200s gaps must NOT fire rapid layering
SELECT * FROM cypher('aml_network', $$
  CREATE (n0:Entity {id: 'LVRLNEG_A', system: 'FIAT'}),
         (n1:Entity {id: 'LVRLNEG_M1', system: 'FIAT'}),
         (n2:Entity {id: 'LVRLNEG_M2', system: 'FIAT'}),
         (n3:Entity {id: 'LVRLNEG_M3', system: 'FIAT'}),
         (n4:Entity {id: 'LVRLNEG_N', system: 'FIAT'})
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (a:Entity {id: 'LVRLNEG_A'}), (b:Entity {id: 'LVRLNEG_M1'}),
        (c:Entity {id: 'LVRLNEG_M2'}), (d:Entity {id: 'LVRLNEG_M3'}),
        (e:Entity {id: 'LVRLNEG_N'})
  CREATE (a)-[:Transfer {amount_usd: 500, ts: 1725000000, ref_id: 'LVRLNEG_TX_1'}]->(b),
         (b)-[:Transfer {amount_usd: 500, ts: 1725007200, ref_id: 'LVRLNEG_TX_2'}]->(c),
         (c)-[:Transfer {amount_usd: 500, ts: 1725014400, ref_id: 'LVRLNEG_TX_3'}]->(d),
         (d)-[:Transfer {amount_usd: 500, ts: 1725021600, ref_id: 'LVRLNEG_TX_4'}]->(e)
$$) as (v agtype);

-- cross-rail fixture: USDT inflow -> same-UBO fiat outflow within 1h
SELECT * FROM cypher('aml_network', $$
  CREATE (w:Entity {id: 'LVCR_WALLET', system: 'ETHEREUM'}),
         (s:Entity {id: 'LVCR_SRC', system: 'ETHEREUM'}),
         (f:Entity {id: 'LVCR_FIAT', system: 'FIAT'}),
         (d:Entity {id: 'LVCR_DST', system: 'FIAT'}),
         (p:Party {id: 'LVCR_UBO', display_name: 'Live Verify UBO'})
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (s:Entity {id: 'LVCR_SRC'}), (w:Entity {id: 'LVCR_WALLET'}),
        (f:Entity {id: 'LVCR_FIAT'}), (d:Entity {id: 'LVCR_DST'}),
        (p:Party {id: 'LVCR_UBO'})
  CREATE (s)-[:Transfer {amount_usd: 50000, ts: 1725000000, asset: 'USDT', ref_id: 'LVCR_IN'}]->(w),
         (f)-[:Transfer {amount_usd: 48000, ts: 1725003600, ref_id: 'LVCR_OUT'}]->(d),
         (w)-[:OWNED_BY]->(p), (f)-[:OWNED_BY]->(p)
$$) as (v agtype);

-- auth-drift fixture: ever-authorized wallet, revoked, transacting
SELECT * FROM cypher('aml_network', $$
  CREATE (a:Entity {id: 'LVAD_STALE', system: 'SOLANA', authorized: false, ever_authorized: true}),
         (b:Entity {id: 'LVAD_DST', system: 'SOLANA'})
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (a:Entity {id: 'LVAD_STALE'}), (b:Entity {id: 'LVAD_DST'})
  CREATE (a)-[:Transfer {amount_usd: 300, ts: 1725000500, ref_id: 'LVAD_TX'}]->(b)
$$) as (v agtype);
