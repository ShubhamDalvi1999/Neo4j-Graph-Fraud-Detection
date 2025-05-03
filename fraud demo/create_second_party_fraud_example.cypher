// Fix Demo Fraud Network Data
// This script recreates the demo data using MERGE to ensure nodes exist and are properly connected

// First check if any demo data already exists
MATCH (n:DemoClient)
RETURN count(n) as ExistingDemoNodes;

// Clear any existing demo data to start fresh
MATCH (n:DemoClient)
DETACH DELETE n;

// Create demo first-party fraudsters (more explicit approach)
MERGE (c1:Client:FirstPartyFraudster:DemoClient {id: 'demo-fp-1', name: 'DEMO-FP-Smith'})
SET c1.firstPartyFraudScore = 0.85, c1.demoData = true;

MERGE (c2:Client:FirstPartyFraudster:DemoClient {id: 'demo-fp-2', name: 'DEMO-FP-Jones'})
SET c2.firstPartyFraudScore = 0.92, c2.demoData = true;

MERGE (c3:Client:FirstPartyFraudster:DemoClient {id: 'demo-fp-3', name: 'DEMO-FP-Davis'})
SET c3.firstPartyFraudScore = 0.78, c3.demoData = true;

// Create demo money mules
MERGE (m1:Client:SecondPartyFraud:DemoClient {id: 'demo-sp-1', name: 'DEMO-SP-Johnson'})
SET m1.secondPartyFraudScore = 0.95, m1.demoData = true;

MERGE (m2:Client:SecondPartyFraud:DemoClient {id: 'demo-sp-2', name: 'DEMO-SP-Williams'})
SET m2.secondPartyFraudScore = 0.89, m2.demoData = true;

// Create demo destination accounts
MERGE (d1:Client:DemoClient {id: 'demo-dest-1', name: 'DEMO-DEST-Brown'})
SET d1.demoData = true;

MERGE (d2:Client:DemoClient {id: 'demo-dest-2', name: 'DEMO-DEST-Miller'})
SET d2.demoData = true;

// Create relationships using direct MERGE with explicit node references
// First-party fraudsters transfer to primary money mule
MATCH (c1:DemoClient {id: 'demo-fp-1'}), (m1:DemoClient {id: 'demo-sp-1'})
MERGE (c1)-[r1:TRANSFER_TO]->(m1)
SET r1.amount = 7500, r1.timestamp = datetime('2023-06-10'), r1.demoData = true;

MATCH (c2:DemoClient {id: 'demo-fp-2'}), (m1:DemoClient {id: 'demo-sp-1'})
MERGE (c2)-[r2:TRANSFER_TO]->(m1)
SET r2.amount = 8200, r2.timestamp = datetime('2023-06-12'), r2.demoData = true;

MATCH (c3:DemoClient {id: 'demo-fp-3'}), (m1:DemoClient {id: 'demo-sp-1'})
MERGE (c3)-[r3:TRANSFER_TO]->(m1)
SET r3.amount = 6800, r3.timestamp = datetime('2023-06-14'), r3.demoData = true;

// First-party fraudster also transfers to secondary money mule
MATCH (c3:DemoClient {id: 'demo-fp-3'}), (m2:DemoClient {id: 'demo-sp-2'})
MERGE (c3)-[r4:TRANSFER_TO]->(m2)
SET r4.amount = 5000, r4.timestamp = datetime('2023-06-15'), r4.demoData = true;

// Money mules transfer to each other
MATCH (m1:DemoClient {id: 'demo-sp-1'}), (m2:DemoClient {id: 'demo-sp-2'})
MERGE (m1)-[r5:TRANSFER_TO]->(m2)
SET r5.amount = 4500, r5.timestamp = datetime('2023-06-16'), r5.demoData = true;

// Money mules transfer to final destinations
MATCH (m1:DemoClient {id: 'demo-sp-1'}), (d1:DemoClient {id: 'demo-dest-1'})
MERGE (m1)-[r6:TRANSFER_TO]->(d1)
SET r6.amount = 12000, r6.timestamp = datetime('2023-06-17'), r6.demoData = true;

MATCH (m2:DemoClient {id: 'demo-sp-2'}), (d2:DemoClient {id: 'demo-dest-2'})
MERGE (m2)-[r7:TRANSFER_TO]->(d2)
SET r7.amount = 9000, r7.timestamp = datetime('2023-06-18'), r7.demoData = true;

MATCH (m2:DemoClient {id: 'demo-sp-2'}), (d1:DemoClient {id: 'demo-dest-1'})
MERGE (m2)-[r8:TRANSFER_TO]->(d1)
SET r8.amount = 6500, r8.timestamp = datetime('2023-06-19'), r8.demoData = true;

// Verify the data was created correctly
MATCH (n:DemoClient)
RETURN count(n) as DemoNodeCount;

MATCH (:DemoClient)-[r]->(:DemoClient)
RETURN count(r) as DemoRelationshipCount;

// A simple visualization query to test the demo network
MATCH path = (:DemoClient)-[:TRANSFER_TO]->(:DemoClient)
RETURN path; 