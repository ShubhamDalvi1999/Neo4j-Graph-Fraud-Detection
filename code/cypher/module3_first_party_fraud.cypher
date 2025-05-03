// ============================================================================
// MODULE 3: FIRST-PARTY FRAUD DETECTION - GRAPH FRAUD DETECTION
// ============================================================================

// This module implements these steps:
// 1. Identifying clients sharing PII
// 2. Creating fraud rings using community detection (WCC)
// 3. Finding similar clients with Node Similarity
// 4. Calculating fraud scores with centrality algorithms
// 5. Identifying potential fraudsters

// ============================================================================
// EXERCISE 1: IDENTIFYING SHARED PII
// ============================================================================

// Task 1: Identify pairs of clients sharing PII
// --------------------------------------------
MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
<-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
WHERE c1.id<>c2.id
RETURN c1.id, c2.id, count(*) AS freq 
ORDER BY freq DESC;

// Count unique clients sharing PII
MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
<-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
WHERE c1.id<>c2.id
RETURN count(DISTINCT c1.id) AS freq;

// Task 2: Create a new relationship between clients sharing PII
// -----------------------------------------------------------
MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
<-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
WHERE c1.id<>c2.id
WITH c1, c2, count(*) as cnt
MERGE (c1)-[:SHARED_IDENTIFIERS {count: cnt}]-(c2);

// Visualize the new relationships (limited to 25)
MATCH p = (c:Client)-[s:SHARED_IDENTIFIERS]-() 
WHERE s.count >= 2 
RETURN p LIMIT 25;

// ============================================================================
// EXERCISE 2: IDENTIFYING FRAUD CLUSTERS USING WCC
// ============================================================================

// Task 1: Memory estimation
// -----------------------
CALL gds.graph.project.cypher.estimate(
  'MATCH (c:Client) RETURN id(c) AS id',
  'MATCH (c1:Client)-[r:SHARED_IDENTIFIERS]-(c2:Client)
   WHERE c1.id<>c2.id
   RETURN id(c1) AS source, id(c2) AS target, r.count AS weight'
) YIELD requiredMemory, nodeCount, relationshipCount;

// Task 2: Drop existing graph if it exists
// --------------------------------------
CALL gds.graph.exists('WCC') YIELD exists
WITH exists
WHERE exists
CALL gds.graph.drop('WCC')
YIELD graphName
RETURN 'Dropped existing graph: ' + graphName;

// Create graph projection for WCC
// -----------------------------
CALL gds.graph.project('WCC', 'Client',
  {
    SHARED_IDENTIFIERS: {
      type: 'SHARED_IDENTIFIERS',
      properties: {
        count: {
          property: 'count'
        }
      }
    }
  }
) YIELD graphName, nodeCount, relationshipCount, projectMillis;

// Task 3: Pre-execution checks
// --------------------------
CALL gds.wcc.stream.estimate('WCC', {})
YIELD nodeCount, relationshipCount, bytesMin, bytesMax;

CALL gds.wcc.stats('WCC');

// Task 4: Execute WCC algorithm in stream mode
// ------------------------------------------
CALL gds.wcc.stream('WCC')
YIELD componentId, nodeId
WITH componentId AS cluster, gds.util.asNode(nodeId) AS client
WITH cluster, collect(client.id) AS clients
WITH *, size(clients) AS clusterSize
WHERE clusterSize > 1
RETURN cluster, clusterSize, clients
ORDER BY clusterSize DESC;

// Task 5: Write results to the database
// -----------------------------------
CALL gds.wcc.stream('WCC')
YIELD componentId, nodeId
WITH componentId AS cluster, gds.util.asNode(nodeId) AS client
WITH cluster, collect(client.id) AS clients
WITH *, size(clients) AS clusterSize
WHERE clusterSize > 1
UNWIND clients AS client
MATCH (c:Client)
WHERE c.id = client
SET c.firstPartyFraudGroup = cluster;

// Task 6: Visualize clusters
// ------------------------
MATCH (c:Client)
WITH c.firstPartyFraudGroup AS fpGroupID, collect(c.id) AS fGroup
WITH *, size(fGroup) AS groupSize 
WHERE groupSize >= 9
WITH collect(fpGroupID) AS fraudRings
MATCH p = (c:Client)-[:HAS_SSN|HAS_EMAIL|HAS_PHONE]->()
WHERE c.firstPartyFraudGroup IN fraudRings
RETURN p;

// ============================================================================
// EXERCISE 3: FINDING SIMILAR CLIENTS USING NODE SIMILARITY
// ============================================================================

// Task 1: Drop existing graph if it exists
// --------------------------------------
CALL gds.graph.exists('Similarity') YIELD exists
WITH exists
WHERE exists
CALL gds.graph.drop('Similarity')
YIELD graphName
RETURN 'Dropped existing graph: ' + graphName;

// Create a graph for node similarity
// --------------------------------
CALL gds.graph.project.cypher('Similarity',
  'MATCH (c:Client)
   WHERE c.firstPartyFraudGroup IS NOT NULL
   RETURN id(c) AS id, labels(c) AS labels
   UNION
   MATCH (n)
   WHERE n:Email OR n:Phone OR n:SSN
   RETURN id(n) AS id, labels(n) AS labels',
  'MATCH (c:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(ids)
   WHERE c.firstPartyFraudGroup IS NOT NULL
   RETURN id(c) AS source, id(ids) AS target'
) YIELD graphName, nodeCount, relationshipCount, projectMillis;

// Task 2: Stream node similarity results
// ------------------------------------
CALL gds.nodeSimilarity.stream('Similarity', {topK: 15})
YIELD node1, node2, similarity
RETURN gds.util.asNode(node1).id AS client1,
       gds.util.asNode(node2).id AS client2,
       similarity
ORDER BY similarity;

// Task 3: Mutate the in-memory graph with similarity results
// --------------------------------------------------------
CALL gds.nodeSimilarity.mutate('Similarity', 
  {
    topK: 15,
    mutateProperty: 'jaccardScore', 
    mutateRelationshipType: 'SIMILAR_TO'
  }
);

// Task 4: Write similarity relationships to the database
// ---------------------------------------------------
CALL gds.graph.writeRelationship('Similarity', 'SIMILAR_TO', 'jaccardScore');

// Task 5: Visualize similarity relationships
// ---------------------------------------
MATCH (c:Client)
WITH c.firstPartyFraudGroup AS fpGroupID, collect(c.id) AS fGroup
WITH *, size(fGroup) AS groupSize 
WHERE groupSize >= 9
WITH collect(fpGroupID) AS fraudRings
MATCH p = (c:Client)-[:SIMILAR_TO]->()
WHERE c.firstPartyFraudGroup IN fraudRings
RETURN p;

// ============================================================================
// EXERCISE 4: CALCULATING FIRST-PARTY FRAUD SCORES
// ============================================================================

// Task 1: Calculate degree centrality scores
// ---------------------------------------
CALL gds.degree.stream('Similarity',
  {
    nodeLabels: ['Client'],
    relationshipTypes: ['SIMILAR_TO'],
    relationshipWeightProperty: 'jaccardScore'
  }
)
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).id AS client, score
ORDER BY score DESC;

// Task 2: Write centrality scores to the database
// --------------------------------------------
CALL gds.degree.write('Similarity',
  {
    nodeLabels: ['Client'],
    relationshipTypes: ['SIMILAR_TO'],
    relationshipWeightProperty: 'jaccardScore',
    writeProperty: 'firstPartyFraudScore'
  }
);

// Task 3: Label potential fraudsters
// -------------------------------
// Identify clients with fraud scores above the 80th percentile
MATCH (c:Client)
WHERE c.firstPartyFraudScore IS NOT NULL
WITH percentileCont(c.firstPartyFraudScore, 0.8) AS firstPartyFraudThreshold
MATCH (c:Client)
WHERE c.firstPartyFraudScore > firstPartyFraudThreshold
SET c:FirstPartyFraudster;

// ============================================================================
// CLEANUP
// ============================================================================

// Clean up graphs (uncomment to remove the graphs)
// CALL gds.graph.drop('WCC');
// CALL gds.graph.drop('Similarity'); 