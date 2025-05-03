// ============================================================================
// MODULE 2: PRELIMINARY DATA ANALYSIS - GRAPH FRAUD DETECTION
// ============================================================================

// This module explores the dataset and collects statistics on:
// - Database schema and size
// - Node labels and relationship types distributions
// - Node and relationship properties
// - Transaction type distribution

// Database Schema Visualization
// ----------------------------
// Run this query to visualize the database schema
CALL db.schema.visualization();

// Database Statistics using APOC
// -----------------------------
CALL apoc.meta.stats();

// Node Label Statistics
// --------------------
CALL db.labels() YIELD label
CALL apoc.cypher.run('MATCH (:`'+label+'`) RETURN count(*) as freq',{})
YIELD value
WITH label,value.freq AS freq
CALL apoc.meta.stats() YIELD nodeCount
WITH *,3 AS presicion
WITH *,10^presicion AS factor,toFloat(freq)/toFloat(nodeCount) AS relFreq
RETURN label AS nodeLabel, freq AS frequency,round(relFreq*factor)/factor AS relativeFrequency 
ORDER BY freq DESC;

// Relationship Type Statistics
// --------------------------
CALL db.relationshipTypes() YIELD relationshipType as type
CALL apoc.cypher.run('MATCH ()-[:`'+type+'`]->() RETURN count(*) as freq',{})
YIELD value
WITH type AS relationshipType, value.freq AS freq
CALL apoc.meta.stats() YIELD relCount
WITH *,3 AS presicion
WITH *, 10^presicion AS factor,toFloat(freq)/toFloat(relCount) as relFreq
RETURN relationshipType, freq AS frequency,
    round(relFreq*factor)/factor AS relativeFrequency
ORDER BY freq DESC;

// Node and Relationship Properties
// ------------------------------
CALL apoc.meta.data() YIELD label,property,type,elementType
WHERE type<>'RELATIONSHIP'
RETURN elementType,label,property,type
ORDER BY elementType,label,property;

// Transaction Type Statistics
// -------------------------
MATCH (t:Transaction)
WITH sum(t.amount) AS globalSum, count(t) AS globalCnt
WITH *, 10^3 AS scaleFactor
UNWIND ['CashIn', 'CashOut', 'Payment', 'Debit', 'Transfer'] AS txType
  CALL apoc.cypher.run('MATCH (t:' + txType + ')
    RETURN sum(t.amount) as txAmount, count(t) AS txCnt', {})
  YIELD value
RETURN txType,value.txAmount AS TotalMarketValue,
  100*round(scaleFactor*(toFloat(value.txAmount)/toFloat(globalSum)))
    /scaleFactor AS `%MarketValue`,
  100*round(scaleFactor*(toFloat(value.txCnt)/toFloat(globalCnt)))
    /scaleFactor AS `%MarketTransactions`,
  toInteger(toFloat(value.txAmount)/toFloat(value.txCnt)) AS AvgTransactionValue,
  value.txCnt AS NumberOfTransactions
ORDER BY `%MarketTransactions` DESC; 