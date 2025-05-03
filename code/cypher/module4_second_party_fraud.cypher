// ============================================================================
// MODULE 4: SECOND-PARTY FRAUD DETECTION - GRAPH FRAUD DETECTION
// ============================================================================

// This module implements these steps:
// 1. Identifying transactions between first-party fraudsters and other clients
// 2. Creating transfer relationship networks
// 3. Detecting fraud networks using community detection and PageRank
// 4. Labeling potential second-party fraudsters

// Note: Before running this module, Module 3 (First-party Fraud Detection) must be completed

// Check if first-party fraud detection has been run
MATCH (c:Client:FirstPartyFraudster) 
RETURN count(c) AS fraudsterCount;

// ============================================================================
// EXERCISE 1: IDENTIFYING TRANSACTIONS BETWEEN FRAUDSTERS AND CLIENTS
// ============================================================================

// Task 1: Find transactions between fraudsters and non-fraudsters
// ------------------------------------------------------------
// Visualize transactions (limited to 10)
MATCH p = (:Client:FirstPartyFraudster)-[]-(:Transaction)-[]-(c:Client)
WHERE NOT c:FirstPartyFraudster
RETURN p LIMIT 10;

// Find transaction types
MATCH (:Client:FirstPartyFraudster)-[]-(txn:Transaction)-[]-(c:Client)
WHERE NOT c:FirstPartyFraudster
UNWIND labels(txn) AS transactionType
RETURN transactionType, count(*) AS freq;

// Task 2: Create TRANSFER_TO relationships from fraudsters to clients
// ----------------------------------------------------------------
// From fraudsters to clients
MATCH (c1:Client:FirstPartyFraudster)-[]->(t:Transaction)-[]->(c2:Client)
WHERE NOT c2:FirstPartyFraudster
WITH c1, c2, sum(t.amount) AS totalAmount
SET c2:SecondPartyFraudSuspect
CREATE (c1)-[:TRANSFER_TO {amount:totalAmount}]->(c2);

// From clients to fraudsters
MATCH (c1:Client:FirstPartyFraudster)<-[]-(t:Transaction)<-[]-(c2:Client)
WITH c1, c2, sum(t.amount) AS totalAmount
CREATE (c1)<-[:TRANSFER_TO {amount:totalAmount}]-(c2);

// Task 3: Visualize TRANSFER_TO relationships
// ----------------------------------------
MATCH p = (:Client:FirstPartyFraudster)-[:TRANSFER_TO]-(c:Client)
WHERE NOT c:FirstPartyFraudster
RETURN p LIMIT 25;

// ============================================================================
// EXERCISE 2: DETECTING SECOND-PARTY FRAUD
// ============================================================================

// Task 1: Drop existing graph if it exists
// --------------------------------------
CALL gds.graph.exists('SecondPartyFraudNetwork') YIELD exists
WITH exists
WHERE exists
CALL gds.graph.drop('SecondPartyFraudNetwork')
YIELD graphName
RETURN 'Dropped existing graph: ' + graphName;

// Create an in-memory graph
// -----------------------
CALL gds.graph.project('SecondPartyFraudNetwork', 'Client', 'TRANSFER_TO',
  {relationshipProperties: ['amount']}
) YIELD graphName, nodeCount, relationshipCount;

// Task 2: Execute WCC to find clusters - stream results
// --------------------------------------------------
CALL gds.wcc.stream('SecondPartyFraudNetwork')
YIELD nodeId, componentId
WITH gds.util.asNode(nodeId) AS client, componentId AS clusterId
WITH clusterId, collect(client.id) AS cluster
WITH clusterId, size(cluster) AS clusterSize, cluster
WHERE clusterSize > 1
RETURN clusterId, clusterSize
ORDER BY clusterSize DESC;

// Write WCC results to the database
// -------------------------------
CALL gds.wcc.stream('SecondPartyFraudNetwork')
YIELD nodeId, componentId
WITH gds.util.asNode(nodeId) AS client, componentId AS clusterId
WITH clusterId, collect(client.id) AS cluster
WITH clusterId, size(cluster) AS clusterSize, cluster
WHERE clusterSize > 1
UNWIND cluster AS client
MATCH (c:Client {id: client})
SET c.secondPartyFraudGroup = clusterId;

// Task 3: Identify second-party fraudsters using PageRank - stream results
// ---------------------------------------------------------------------
CALL gds.pageRank.stream('SecondPartyFraudNetwork',
  {relationshipWeightProperty: 'amount'}
)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS client, score AS pageRankScore
WHERE client.secondPartyFraudGroup IS NOT NULL
RETURN client.secondPartyFraudGroup, client.name, labels(client), pageRankScore
ORDER BY client.secondPartyFraudGroup, pageRankScore DESC;

// Write PageRank results to the database and label second-party fraudsters
// ---------------------------------------------------------------------
CALL gds.pageRank.stream('SecondPartyFraudNetwork',
  {relationshipWeightProperty: 'amount'}
)
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS client, score AS pageRankScore
WHERE client.secondPartyFraudGroup IS NOT NULL
  AND pageRankScore > 1 AND NOT client:FirstPartyFraudster
MATCH(c:Client {id: client.id})
SET c:SecondPartyFraud
SET c.secondPartyFraudScore = pageRankScore;

// Task 4: Visualize second-party fraud networks
// ------------------------------------------
MATCH p = (:Client:FirstPartyFraudster)-[:TRANSFER_TO]-(c:Client:SecondPartyFraud)
RETURN p;

// ============================================================================
// FRAUD SUMMARY
// ============================================================================

// Get counts of identified fraudsters
MATCH (c:Client:FirstPartyFraudster) 
RETURN count(c) AS firstPartyFraudCount;

MATCH (c:Client:SecondPartyFraud) 
RETURN count(c) AS secondPartyFraudCount;

// Combined visualization of all fraudsters
MATCH p = (f1:Client:FirstPartyFraudster)-[:TRANSFER_TO]-(f2:Client:SecondPartyFraud)
RETURN p LIMIT 100;

// ============================================================================
// CLEANUP
// ============================================================================

// Clean up graph (uncomment to remove)
// CALL gds.graph.drop('SecondPartyFraudNetwork'); 