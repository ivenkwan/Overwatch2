-- TASK-061/062 fixture cleanup (run after the live verification).
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

SELECT * FROM cypher('aml_network', $$
  MATCH (n:Entity) WHERE n.id STARTS WITH 'LV' DETACH DELETE n
$$) as (v agtype);
SELECT * FROM cypher('aml_network', $$
  MATCH (p:Party) WHERE p.id STARTS WITH 'LV' DETACH DELETE p
$$) as (v agtype);
DELETE FROM app.alerts WHERE payload->>'rule_version' = '2026.09-aml-detection-workbench';
