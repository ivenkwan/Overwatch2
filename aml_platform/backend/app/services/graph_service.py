import asyncpg
import json

async def parse_agtype(db: asyncpg.Connection, val):
    # Depending on how asyncpg returns agtype (usually as a string)
    if val is None:
        return None
    # We can just fetch them as raw properties in the query instead!
    return val

async def get_full_network(db: asyncpg.Connection, limit: int) -> list:
    # Safest way to query Apache AGE without getting stuck in string parsing
    query = f"""
    SELECT * FROM cypher('tap_and_go_network', $$
        MATCH (n)-[r]->(m) 
        RETURN properties(n), id(n), label(n), properties(r), id(r), label(r), properties(m), id(m), label(m)
        LIMIT {limit}
    $$) AS (n_prop agtype, n_id agtype, n_lbl agtype, r_prop agtype, r_id agtype, r_lbl agtype, m_prop agtype, m_id agtype, m_lbl agtype);
    """
    
    rows = await db.fetch(query)
    elements = []
    seen_nodes = set()
    
    for r in rows:
        # asyncpg will return agtype strings like '{"id": "..."}' we can json.loads
        try:
            n_prop = json.loads(r['n_prop']) if r['n_prop'] else {}
            m_prop = json.loads(r['m_prop']) if r['m_prop'] else {}
            
            n_id = str(r['n_id'])
            m_id = str(r['m_id'])
            
            # Add Source Node
            if n_id not in seen_nodes:
                elements.append({
                    "data": {**n_prop, "id": n_id, "label": str(r['n_lbl']).strip('"')}
                })
                seen_nodes.add(n_id)
                
            # Add Target Node
            if m_id not in seen_nodes:
                elements.append({
                    "data": {**m_prop, "id": m_id, "label": str(r['m_lbl']).strip('"')}
                })
                seen_nodes.add(m_id)
                
            # Add Edge
            r_prop = json.loads(r['r_prop']) if r['r_prop'] else {}
            r_type = str(r['r_lbl']).strip('"')
            r_edge_id = str(r['r_id'])
            
            elements.append({
                "data": {
                    "id": f"edge_{r_edge_id}",
                    "source": n_id,
                    "target": m_id,
                    "label": r_type,
                    **r_prop
                }
            })
            
        except Exception as e:
            print("Error parsing row graph elements:", e)
            continue
            
    return elements

async def get_neighborhood(db: asyncpg.Connection, entity_id: str, depth: int) -> list:
    """Fetches a subgraph centered around entity_id up to 'depth' hops away."""
    entity_id_clean = str(entity_id).replace("'", "''")
    depth_clean = max(1, min(int(depth), 6))
    
    query = f"""
    SELECT * FROM cypher('tap_and_go_network', $$
        MATCH path=(root {{id: '{entity_id_clean}'}})-[*1..{depth_clean}]-(m)
        UNWIND relationships(path) AS rel
        WITH DISTINCT rel
        RETURN properties(startNode(rel)), id(startNode(rel)), label(startNode(rel)), 
               properties(rel), id(rel), label(rel), 
               properties(endNode(rel)), id(endNode(rel)), label(endNode(rel))
    $$) AS (n_prop agtype, n_id agtype, n_lbl agtype, r_prop agtype, r_id agtype, r_lbl agtype, m_prop agtype, m_id agtype, m_lbl agtype);
    """
    
    rows = await db.fetch(query)
    elements = []
    seen_nodes = set()
    
    for r in rows:
        try:
            n_prop = json.loads(r['n_prop']) if r['n_prop'] else {}
            m_prop = json.loads(r['m_prop']) if r['m_prop'] else {}
            
            n_id = str(r['n_id'])
            m_id = str(r['m_id'])
            
            if n_id not in seen_nodes:
                elements.append({"data": {**n_prop, "id": n_id, "label": str(r['n_lbl']).strip('"')}})
                seen_nodes.add(n_id)
                
            if m_id not in seen_nodes:
                elements.append({"data": {**m_prop, "id": m_id, "label": str(r['m_lbl']).strip('"')}})
                seen_nodes.add(m_id)
                
            r_prop = json.loads(r['r_prop']) if r['r_prop'] else {}
            elements.append({
                "data": {
                    "id": f"edge_{r['r_id']}",
                    "source": n_id,
                    "target": m_id,
                    "label": str(r['r_lbl']).strip('"'),
                    **r_prop
                }
            })
        except Exception as e:
            continue
            
    return elements
