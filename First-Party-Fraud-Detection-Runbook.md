# First-Party Fraud Detection Runbook

This runbook outlines the step-by-step process for detecting first-party (synthetic identity) fraud using Neo4j Graph Data Science with the fraud-detection-40 dump data.

## Overview

First-party fraud detection identifies potential synthetic identities by analyzing shared personally identifiable information (PII) across client accounts. The process uses graph algorithms to identify clusters of related identities that may represent fraud rings.

## Prerequisites

1. Neo4j database is running with the fraud-detection-40 dump data loaded
2. Neo4j Graph Data Science (GDS) library is installed
3. APOC library is installed
4. Access to Neo4j Browser (http://localhost:7474)

## Process Steps

### 1. Identifying Shared PII

- The system identifies clients who share the same personally identifiable information (PII) like email addresses, phone numbers, and SSNs
- Execute the `sharedIdentifiers.cypher` script to match pairs of clients connecting to the same PII nodes
- For each pair of clients, the script counts shared PII elements and creates a `SHARED_IDENTIFIERS` relationship with a `count` property

```cypher
// Run this in Neo4j Browser
MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
<-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
WHERE c1.id<>c2.id
WITH c1, c2, count(*) as cnt
MERGE (c1) - [:SHARED_IDENTIFIERS {count: cnt}] - (c2);
```

**Verification:**
```cypher
// Check the number of SHARED_IDENTIFIERS relationships created
MATCH ()-[r:SHARED_IDENTIFIERS]->() RETURN COUNT(r);
```

### 2. Creating a Graph Projection

- Execute the `loadWCCNamedGraph.cypher` script to create a projected graph named 'WCC' in Neo4j Graph Data Science
- This projection includes only Client nodes and SHARED_IDENTIFIERS relationships with their count properties
- The projection allows efficient algorithm execution on this subset of the data

```cypher
CALL gds.graph.create('WCC', 'Client',
    {
        SHARED_IDENTIFIERS:{
            type: 'SHARED_IDENTIFIERS',
            properties: {
                count: {
                    property: 'count'
                }
            }
        }
    }
) YIELD graphName,nodeCount,relationshipCount,projectMillis;
```

**Verification:**
```cypher
// Verify the graph projection exists
CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount
WHERE graphName = 'WCC'
RETURN graphName, nodeCount, relationshipCount;
```

### 3. Running Weakly Connected Components

- Execute the `wccWrite.cypher` script to run the Weakly Connected Components algorithm on the projected graph
- WCC identifies clusters of interconnected clients who share PII information
- Only clusters with more than one client are considered (potential fraud rings)
- Each client in these clusters gets a `firstPartyFraudGroup` property set to their component ID

```cypher
CALL gds.wcc.stream('WCC')
YIELD componentId,nodeId
WITH componentId AS cluster,gds.util.asNode(nodeId) AS client
WITH cluster, collect(client.id) AS clients
WITH *,size(clients) AS clusterSize
WHERE clusterSize>1
UNWIND clients AS client
MATCH(c:Client) 
WHERE c.id=client
SET c.firstPartyFraudGroup=cluster;
```

**Verification:**
```cypher
// Count clients assigned to fraud groups
MATCH (c:Client)
WHERE exists(c.firstPartyFraudGroup)
RETURN COUNT(c);

// View fraud groups and their sizes
MATCH (c:Client)
WHERE exists(c.firstPartyFraudGroup)
WITH c.firstPartyFraudGroup AS fraudGroup, count(*) AS groupSize
RETURN fraudGroup, groupSize
ORDER BY groupSize DESC
LIMIT 10;
```

### 4. Computing Node Similarity

- The system calculates similarity scores between clients using the Jaccard similarity algorithm
- This creates `SIMILAR_TO` relationships between clients with a `jaccardScore` property
- The `jaccardScore` indicates how similar two clients are based on their shared identifiers

```cypher
// Create a similarity graph projection
CALL gds.graph.project('similarity',
    'Client',
    'SHARED_IDENTIFIERS',
    {
        relationshipProperties: 'count'
    }
);

// Run the Node Similarity algorithm and mutate the graph
CALL gds.nodeSimilarity.mutate('similarity',
    {
        topK: 10,
        mutateProperty: 'jaccardScore',
        mutateRelationshipType: 'SIMILAR_TO'
    }
);
```

**Verification:**
```cypher
// Verify SIMILAR_TO relationships in the projection
CALL gds.graph.relationshipTypes('similarity')
YIELD relationshipType
RETURN relationshipType;
```

### 5. Calculating Fraud Scores

- Execute the `degreeWrite.cypher` script to assign a `firstPartyFraudScore` to each client
- Uses a weighted degree centrality algorithm
- This score is derived from the sum of jaccard similarity scores on incoming `SIMILAR_TO` relationships
- Clients with higher scores have more connections to other suspicious clients, making them potentially higher risk

```cypher
CALL gds.degree.write('similarity',
    {
        nodeLabels: ['Client'],
        relationshipTypes: ['SIMILAR_TO'],
        relationshipWeightProperty: 'jaccardScore',
        writeProperty: 'firstPartyFraudScore'
    }
);
```

**Verification:**
```cypher
// Check distribution of fraud scores
MATCH (c:Client)
WHERE exists(c.firstPartyFraudScore)
RETURN 
    count(*) AS totalScoredClients,
    min(c.firstPartyFraudScore) AS minScore,
    max(c.firstPartyFraudScore) AS maxScore,
    avg(c.firstPartyFraudScore) AS avgScore,
    percentileCont(c.firstPartyFraudScore, 0.8) AS percentile80;
```

### 6. Identifying First-Party Fraudsters

- Execute the `firstPartyFraudScoreWrite.cypher` script to identify clients with fraud scores above a threshold
- The threshold is set at the 80th percentile of all fraud scores
- Clients exceeding this threshold are labeled as `:FirstPartyFraudster`

```cypher
MATCH(c:Client) 
WHERE exists(c.firstPartyFraudScore)
WITH percentileCont(c.firstPartyFraudScore, 0.8)
    AS firstPartyFraudThreshold
MATCH(c:Client)
WHERE c.firstPartyFraudScore>firstPartyFraudThreshold
SET c:FirstPartyFraudster;
```

**Verification:**
```cypher
// Count identified fraudsters
MATCH (c:FirstPartyFraudster)
RETURN COUNT(c);

// View top fraudsters by score
MATCH (c:Client:FirstPartyFraudster)
RETURN c.name, c.firstPartyFraudScore
ORDER BY c.firstPartyFraudScore DESC
LIMIT 25;
```

### 7. Visualization

- Execute the `visualizeSharedIdentifiers.cypher` script to visualize relationships between clients
- Shows connections between clients who share at least 2 PII elements

```cypher
MATCH p = (c:Client) - [s:SHARED_IDENTIFIERS] - () WHERE s.count >= 2 RETURN p LIMIT 25;
```

**Additional Visualization Queries:**

```cypher
// Visualize identified fraudsters and their connections
MATCH p = (c1:Client:FirstPartyFraudster)-[:SHARED_IDENTIFIERS]-(c2:Client)
WHERE c2:FirstPartyFraudster
RETURN p
LIMIT 50;

// Visualize fraud groups
MATCH (c:Client)
WHERE exists(c.firstPartyFraudGroup)
WITH c.firstPartyFraudGroup AS fraudGroup, collect(c) AS clients
WHERE size(clients) <= 25 AND size(clients) > 1
WITH clients
UNWIND clients AS c1
UNWIND clients AS c2
WHERE id(c1) < id(c2)
MATCH p = (c1)-[:SHARED_IDENTIFIERS]-(c2)
RETURN p;
```

## Execution Order

For proper execution, follow these steps in order:
1. Run `sharedIdentifiers.cypher` (Step 1)
2. Run `loadWCCNamedGraph.cypher` (Step 2)
3. Run `wccWrite.cypher` (Step 3)
4. Generate similarity scores (Step 4)
5. Run `degreeWrite.cypher` (Step 5)
6. Run `firstPartyFraudScoreWrite.cypher` (Step 6)
7. Run `visualizeSharedIdentifiers.cypher` (Step 7)

## Accessing Neo4j Browser

1. Open your web browser and navigate to http://localhost:7474
2. Log in with username `neo4j` and password specified in your configuration (default: `neopass2025`)
3. Paste and execute Cypher queries in the command input at the top of the browser

## Troubleshooting

If any step fails:

1. **Graph already exists**: If you get an error saying a graph projection already exists, you can remove it:
   ```cypher
   CALL gds.graph.drop('WCC');
   CALL gds.graph.drop('similarity');
   ```

2. **No results in Step 1**: Verify that PII relationships exist:
   ```cypher
   MATCH ()-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->() RETURN COUNT(*);
   ```

3. **Missing GDS functions**: Ensure the Graph Data Science library is properly installed and loaded:
   ```cypher
   RETURN gds.version();
   ```

4. **Memory issues**: If you experience memory issues, consider dropping projections after use:
   ```cypher
   CALL gds.graph.drop('WCC');
   CALL gds.graph.drop('similarity');
   ```

## Notes

- The Neo4j database must be populated with the fraud-detection-40 dump data before executing these steps
- All scripts should be run in the Neo4j Browser connected to your database instance
- The Graph Data Science library must be installed and properly configured 