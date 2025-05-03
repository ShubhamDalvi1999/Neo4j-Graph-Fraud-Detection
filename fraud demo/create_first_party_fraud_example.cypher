// Create First Party Fraud Example Data
// This script creates a demonstration of first-party fraud with shared PII elements

// First check if any demo data already exists
MATCH (n:DemoFirstParty)
RETURN count(n) as ExistingDemoNodes;

// Clear any existing first-party demo data to start fresh
MATCH (n:DemoFirstParty)
DETACH DELETE n;

// Create client nodes
MERGE (madison:Client:FirstPartyFraudster:DemoFirstParty {
  id: 'demo-madison', 
  name: 'Madison Ferrell',
  demoData: true,
  firstPartyFraudScore: 0.89
});

MERGE (ian:Client:FirstPartyFraudster:DemoFirstParty {
  id: 'demo-ian', 
  name: 'Ian Gregory',
  demoData: true,
  firstPartyFraudScore: 0.92
});

// Create PII nodes
MERGE (email:Email:DemoFirstParty {
  id: 'johnfrazier67@mail.co-m',
  value: 'johnfrazier67@mail.co-m',
  demoData: true
});

MERGE (phone:Phone:DemoFirstParty {
  id: '446-870-2234',
  value: '446-870-2234',
  demoData: true
});

MERGE (ssn:SSN:DemoFirstParty {
  id: '555-93-5211',
  value: '555-93-5211',
  demoData: true
});

// Create HAS_EMAIL, HAS_PHONE, and HAS_SSN relationships
MERGE (madison)-[:HAS_EMAIL {demoData: true}]->(email);
MERGE (ian)-[:HAS_EMAIL {demoData: true}]->(email);

MERGE (madison)-[:HAS_PHONE {demoData: true}]->(phone);
MERGE (ian)-[:HAS_PHONE {demoData: true}]->(phone);

MERGE (madison)-[:HAS_SSN {demoData: true}]->(ssn);
MERGE (ian)-[:HAS_SSN {demoData: true}]->(ssn);

// Create SHARED_IDENTIFIERS relationship between the clients
MATCH (madison:DemoFirstParty {name: 'Madison Ferrell'})
MATCH (ian:DemoFirstParty {name: 'Ian Gregory'})
MERGE (madison)-[r:SHARED_IDENTIFIERS {count: 3, demoData: true}]->(ian);

// Verify data was created correctly
MATCH (n:DemoFirstParty)
RETURN count(n) as DemoFirstPartyNodeCount;

MATCH (:DemoFirstParty)-[r]->(:DemoFirstParty)
RETURN count(r) as DemoFirstPartyRelationshipCount;

// Sample query to view the created graph
MATCH p = (:Client:DemoFirstParty)-[:HAS_EMAIL|HAS_PHONE|HAS_SSN]->(:DemoFirstParty)
RETURN p; 