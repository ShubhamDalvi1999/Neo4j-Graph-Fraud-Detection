// Neo4j First-Party Fraud Visualization Query
// This query visualizes the synthetic identity pattern for Madison Ferrell and Ian Gregory

// Option 1: View the entire first-party fraud example with all PII connections
MATCH (c1:Client:DemoFirstParty {name: 'Madison Ferrell'})
MATCH (c2:Client:DemoFirstParty {name: 'Ian Gregory'})
MATCH (c1)-[r:SHARED_IDENTIFIERS]-(c2)
OPTIONAL MATCH (c1)-[pii1:HAS_EMAIL|HAS_PHONE|HAS_SSN]->(info)<-[pii2:HAS_EMAIL|HAS_PHONE|HAS_SSN]-(c2)
RETURN c1, c2, r, info, pii1, pii2

UNION

// Option 2: More general query similar to the original, but limited to demo data
MATCH (c1:Client:FirstPartyFraudster:DemoFirstParty)-[r:SHARED_IDENTIFIERS]-(c2:Client:FirstPartyFraudster:DemoFirstParty)
WITH c1, c2, r
ORDER BY r.count DESC
LIMIT 10
OPTIONAL MATCH (c1)-[pii1:HAS_EMAIL|HAS_PHONE|HAS_SSN]->(info)<-[pii2:HAS_EMAIL|HAS_PHONE|HAS_SSN]-(c2)
RETURN c1, c2, r, info, pii1, pii2

UNION

// Option 3: Interactive fraud detection visualization
// Shows how a fraud investigator might start with just Madison Ferrell
// and discover connections to Ian Gregory through shared PII
MATCH (start:Client:DemoFirstParty {name: 'Madison Ferrell'})
MATCH path = (start)-[:HAS_EMAIL|HAS_PHONE|HAS_SSN]->()-[:HAS_EMAIL|HAS_PHONE|HAS_SSN]-(:Client)
RETURN path 