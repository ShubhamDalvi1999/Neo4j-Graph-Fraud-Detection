# Second-Party Fraud Detection Runbook

This runbook outlines the step-by-step process for detecting second-party (money mule) fraud using Neo4j Graph Data Science with the fraud-detection-40 dump data.

## Overview

Second-party fraud detection identifies potential money mules by analyzing transfer patterns between accounts. Money mules are individuals who transfer illegally acquired money on behalf of others. The process uses graph algorithms like PageRank to identify suspicious accounts based on transfer patterns.

## Prerequisites

1. Neo4j database is running with the fraud-detection-40 dump data loaded
2. Neo4j Graph Data Science (GDS) library is installed
3. APOC library is installed
4. Access to Neo4j Browser (http://localhost:7474)

## Process Steps

### 1. Creating a Graph Projection

- Execute the following script to create a projected graph named 'SecondPartyFraudNetwork' in Neo4j Graph Data Science
- This projection includes Client nodes and TRANSFER_TO relationships with their amount properties
- The projection allows efficient algorithm execution on this subset of the data

```cypher
CALL gds.graph.project('SecondPartyFraudNetwork', 'Client', 'TRANSFER_TO',
    {relationshipProperties: ['amount']}
) YIELD graphName, nodeCount, relationshipCount;
```

**Verification:**
```cypher
// Verify the graph projection exists
CALL gds.graph.list() YIELD graphName, nodeCount, relationshipCount
WHERE graphName = 'SecondPartyFraudNetwork'
RETURN graphName, nodeCount, relationshipCount;
```

### 2. Running PageRank Algorithm

- Execute the following script to run the PageRank algorithm on the projected graph
- PageRank identifies clients who receive many transfers or high-value transfers from multiple sources
- Accounts with high PageRank scores may be functioning as money mules
- Each client gets a `secondPartyFraudScore` property set to their PageRank value

```cypher
CALL gds.pageRank.write('SecondPartyFraudNetwork',
    {
        maxIterations: 20,
        dampingFactor: 0.85,
        writeProperty: 'secondPartyFraudScore',
        relationshipWeightProperty: 'amount'
    }
) YIELD nodePropertiesWritten, ranIterations;
```

**Verification:**
```cypher
// Count clients assigned fraud scores
MATCH (c:Client)
WHERE exists(c.secondPartyFraudScore)
RETURN COUNT(c);

// View distribution of fraud scores
MATCH (c:Client)
WHERE exists(c.secondPartyFraudScore)
RETURN 
    count(*) AS totalScoredClients,
    min(c.secondPartyFraudScore) AS minScore,
    max(c.secondPartyFraudScore) AS maxScore,
    avg(c.secondPartyFraudScore) AS avgScore,
    percentileCont(c.secondPartyFraudScore, 0.8) AS percentile80;
```

### 3. Identifying Money Mules

- Execute the following script to identify clients with PageRank scores above a threshold
- The threshold is set at the 80th percentile of all PageRank scores
- Clients exceeding this threshold are labeled as `:MoneyMule`

```cypher
MATCH(c:Client) 
WHERE exists(c.secondPartyFraudScore)
WITH percentileCont(c.secondPartyFraudScore, 0.8)
    AS secondPartyFraudThreshold
MATCH(c:Client)
WHERE c.secondPartyFraudScore > secondPartyFraudThreshold
SET c:MoneyMule;
```

**Verification:**
```cypher
// Count identified money mules
MATCH (c:MoneyMule)
RETURN COUNT(c);

// View top money mules by score
MATCH (c:Client:MoneyMule)
RETURN c.name, c.secondPartyFraudScore
ORDER BY c.secondPartyFraudScore DESC
LIMIT 25;
```

### 4. Analyzing Transaction Flow Patterns

- Execute the following script to analyze the transaction flow patterns of suspected money mules
- This identifies clients who receive funds from multiple sources and then transfer those funds elsewhere
- The analysis calculates inflow vs. outflow ratios

```cypher
MATCH (c:Client:MoneyMule)
OPTIONAL MATCH (source:Client)-[inflow:TRANSFER_TO]->(c)
OPTIONAL MATCH (c)-[outflow:TRANSFER_TO]->(target:Client)
WITH c,
    count(distinct source) AS sourcesCount,
    count(distinct target) AS targetsCount,
    sum(inflow.amount) AS totalInflow,
    sum(outflow.amount) AS totalOutflow
WHERE sourcesCount > 3 AND totalOutflow > 0
RETURN 
    c.name,
    c.secondPartyFraudScore,
    sourcesCount,
    targetsCount,
    totalInflow,
    totalOutflow,
    totalInflow/totalOutflow AS flowRatio
ORDER BY c.secondPartyFraudScore DESC
LIMIT 25;
```

### 5. Visualization

- Execute the following script to visualize suspected money mules and their transaction networks
- Shows the flow of funds into and out of suspected money mule accounts

```cypher
// Visualize top money mules and their transaction patterns
MATCH (c:MoneyMule)
WITH c ORDER BY c.secondPartyFraudScore DESC LIMIT 5
MATCH p = (source:Client)-[:TRANSFER_TO]->(c)-[:TRANSFER_TO]->(target:Client)
RETURN p
LIMIT 75;
```

**Additional Visualization Queries:**

```cypher
// Visualize money mule clusters
MATCH (m1:MoneyMule)
WITH m1 ORDER BY m1.secondPartyFraudScore DESC LIMIT 10
MATCH p = (source:Client)-[:TRANSFER_TO]->(m1)
WHERE source:MoneyMule
RETURN p
LIMIT 50;

// Visualize pattern of high-value transfers
MATCH p = (c1:Client)-[t:TRANSFER_TO]->(c2:Client)
WHERE c2:MoneyMule AND t.amount > 5000
RETURN p
LIMIT 50;
```

## Execution Order

For proper execution, follow these steps in order:
1. Create graph projection (Step 1)
2. Run PageRank algorithm (Step 2)
3. Label money mules (Step 3)
4. Analyze transaction patterns (Step 4)
5. Run visualization queries (Step 5)

## Accessing Neo4j Browser

1. Open your web browser and navigate to http://localhost:7474
2. Log in with username `neo4j` and password specified in your configuration (default: `neopass2025`)
3. Paste and execute Cypher queries in the command input at the top of the browser

## Troubleshooting

If any step fails:

1. **Graph already exists**: If you get an error saying a graph projection already exists, you can remove it:
   ```cypher
   CALL gds.graph.drop('SecondPartyFraudNetwork');
   ```

2. **No results in Steps 2 or 3**: Verify that TRANSFER_TO relationships exist:
   ```cypher
   MATCH ()-[r:TRANSFER_TO]->() RETURN COUNT(r);
   ```

3. **Missing GDS functions**: Ensure the Graph Data Science library is properly installed and loaded:
   ```cypher
   RETURN gds.version();
   ```

4. **Memory issues**: If you experience memory issues, consider dropping projections after use:
   ```cypher
   CALL gds.graph.drop('SecondPartyFraudNetwork');
   ```

## Notes

- The Neo4j database must be populated with the fraud-detection-40 dump data before executing these steps
- All scripts should be run in the Neo4j Browser connected to your database instance
- The Graph Data Science library must be installed and properly configured
- This approach focuses on identifying potential money mules, but manual review is necessary to confirm actual fraud cases 