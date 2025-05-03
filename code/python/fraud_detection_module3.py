#!/usr/bin/env python3
"""
Module 3: First-party Fraud Detection - Graph Fraud Detection

This module implements the detection of first-party fraud using graph algorithms.
Steps include:
1. Identifying clients sharing PII
2. Creating clusters using WCC
3. Finding similar clients with Node Similarity
4. Calculating fraud scores
5. Identifying potential fraudsters
"""

import os
import sys
import time
# Ensure the neo4j_connection module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from neo4j_connection import Neo4jConnection

class FirstPartyFraudDetection:
    """Class implementing first-party fraud detection using Neo4j GDS"""
    
    def __init__(self, connection):
        """Initialize with a Neo4j connection
        
        Args:
            connection (Neo4jConnection): An established Neo4j connection
        """
        self.conn = connection
        # Check GDS availability
        self.gds_version = self.conn.check_gds_availability()
        if not self.gds_version:
            raise RuntimeError("Graph Data Science library is required but not available")
        
        # Set graph names (helps with cleanup)
        self.graph_names = []
    
    def cleanup_graphs(self):
        """Remove all graphs created by this instance from the graph catalog"""
        for graph_name in self.graph_names:
            try:
                self.conn.execute_query(
                    f"CALL gds.graph.drop('{graph_name}')", 
                    write=True,
                    description=f"Dropping graph '{graph_name}'"
                )
            except Exception as e:
                print(f"Error dropping graph '{graph_name}': {e}")
    
    def drop_existing_graph(self, graph_name):
        """Drop a graph if it exists to avoid conflicts"""
        try:
            # Check if graph exists
            check_query = f"""
            CALL gds.graph.exists('{graph_name}') 
            YIELD exists
            """
            result = self.conn.execute_query(check_query)
            
            if result and result[0]['exists']:
                # Drop the graph
                self.conn.execute_query(
                    f"CALL gds.graph.drop('{graph_name}')", 
                    write=True,
                    description=f"Dropping existing graph '{graph_name}'"
                )
                print(f"Dropped existing graph '{graph_name}'")
        except Exception as e:
            print(f"Error checking/dropping graph '{graph_name}': {e}")
    
    def identify_shared_pii(self):
        """Identify clients sharing personally identifiable information (PII)"""
        print("\n=== Exercise 1: Identifying Shared PII ===")
        
        # Task 1: Identify pairs of clients sharing PII
        shared_pii_query = """
        MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
        <-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
        WHERE c1.id<>c2.id
        RETURN c1.id,c2.id,count(*) AS freq ORDER BY freq DESC;
        """
        self.conn.run_and_print_query(
            shared_pii_query,
            description="Pairs of clients sharing PII"
        )
        
        # Count unique clients sharing PII
        unique_clients_query = """
        MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
        <-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
        WHERE c1.id<>c2.id
        RETURN count(DISTINCT c1.id) AS freq;
        """
        self.conn.run_and_print_query(
            unique_clients_query,
            description="Number of unique clients sharing PII"
        )
        
        # Task 2: Create a new relationship between clients sharing PII
        create_relationships_query = """
        MATCH (c1:Client)-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(info)
        <-[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]-(c2:Client)
        WHERE c1.id<>c2.id
        WITH c1, c2, count(*) as cnt
        MERGE (c1) - [:SHARED_IDENTIFIERS {count: cnt}] - (c2);
        """
        self.conn.run_and_print_query(
            create_relationships_query,
            write=True,
            description="Creating SHARED_IDENTIFIERS relationships"
        )
        
        # Visualize the new relationships (limited to 25)
        visualize_query = """
        MATCH p = (c:Client) - [s:SHARED_IDENTIFIERS] - () 
        WHERE s.count >= 2 
        RETURN p LIMIT 25;
        """
        print("\nTo visualize the SHARED_IDENTIFIERS relationships, run this query in Neo4j Browser:")
        print(visualize_query)
    
    def detect_fraud_clusters(self):
        """Identify clusters of clients sharing PII using WCC algorithm"""
        print("\n=== Exercise 2: Identifying Fraud Clusters using WCC ===")
        
        # Task 1: Memory estimation
        memory_estimation_query = """
        CALL gds.graph.project.cypher.estimate(
        'MATCH (c:Client) RETURN id(c) AS id',
        'MATCH (c1:Client)-[r:SHARED_IDENTIFIERS]-(c2:Client)
        WHERE c1.id<>c2.id
        RETURN id(c1) AS source,id(c2) AS target,r.count AS weight')
        YIELD requiredMemory,nodeCount,relationshipCount;
        """
        self.conn.run_and_print_query(
            memory_estimation_query,
            description="Memory estimation for WCC graph"
        )
        
        # Task 2: Create graph projection for WCC - first drop if exists
        self.drop_existing_graph('WCC')
        
        create_wcc_graph_query = """
        CALL gds.graph.project('WCC', 'Client',
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
        """
        result = self.conn.run_and_print_query(
            create_wcc_graph_query,
            write=True,
            description="Creating graph projection for WCC"
        )
        
        if result:
            self.graph_names.append('WCC')
        
        # Task 3: Pre-execution checks
        wcc_estimate_query = """
        CALL gds.wcc.stream.estimate('WCC', {}) 
        YIELD nodeCount, relationshipCount, bytesMin, bytesMax;
        """
        self.conn.run_and_print_query(
            wcc_estimate_query,
            description="Memory estimation for WCC algorithm"
        )
        
        wcc_stats_query = """
        CALL gds.wcc.stats('WCC');
        """
        self.conn.run_and_print_query(
            wcc_stats_query,
            description="Statistics for WCC algorithm"
        )
        
        # Task 4: Execute WCC algorithm in stream mode
        wcc_stream_query = """
        CALL gds.wcc.stream('WCC')
        YIELD componentId,nodeId
        WITH componentId AS cluster,gds.util.asNode(nodeId) AS client
        WITH cluster,collect(client.id) AS clients
        WITH *,size(clients) AS clusterSize
        WHERE clusterSize>1
        RETURN cluster,clusterSize,clients
        ORDER by clusterSize DESC;
        """
        self.conn.run_and_print_query(
            wcc_stream_query,
            description="WCC algorithm results (clusters of connected clients)"
        )
        
        # Task 5: Write results to the database
        wcc_write_query = """
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
        """
        self.conn.run_and_print_query(
            wcc_write_query,
            write=True,
            description="Writing WCC results to client nodes"
        )
        
        # Task 6: Visualize clusters
        visualize_clusters_query = """
        MATCH (c:Client)
        WITH c.firstPartyFraudGroup AS fpGroupID, collect(c.id) AS fGroup
        WITH *, size(fGroup) AS groupSize WHERE groupSize >= 9
        WITH collect(fpGroupID) AS fraudRings
        MATCH p=(c:Client)-[:HAS_SSN|HAS_EMAIL|HAS_PHONE]->()
        WHERE c.firstPartyFraudGroup IN fraudRings
        RETURN p
        """
        print("\nTo visualize fraud clusters, run this query in Neo4j Browser:")
        print(visualize_clusters_query)
    
    def find_similar_clients(self):
        """Find similar clients within clusters using Node Similarity"""
        print("\n=== Exercise 3: Finding Similar Clients using Node Similarity ===")
        
        # Task 1: Create a graph for node similarity - first drop if exists
        self.drop_existing_graph('Similarity')
        
        similarity_graph_query = """
        CALL gds.graph.project.cypher('Similarity',
        'MATCH(c:Client)
            WHERE c.firstPartyFraudGroup IS NOT NULL
            RETURN id(c) AS id,labels(c) AS labels
        UNION
        MATCH(n)
            WHERE n:Email OR n:Phone OR n:SSN
            RETURN id(n) AS id,labels(n) AS labels',
        'MATCH(c:Client)
        -[:HAS_EMAIL|:HAS_PHONE|:HAS_SSN]->(ids)
        WHERE c.firstPartyFraudGroup IS NOT NULL
        RETURN id(c) AS source,id(ids) AS target')
        YIELD graphName,nodeCount,relationshipCount,projectMillis;
        """
        result = self.conn.run_and_print_query(
            similarity_graph_query,
            write=True,
            description="Creating graph for Node Similarity"
        )
        
        if result:
            self.graph_names.append('Similarity')
        
        # Task 2: Stream node similarity results
        node_similarity_query = """
        CALL gds.nodeSimilarity.stream('Similarity',{topK:15})
        YIELD node1,node2,similarity
        RETURN gds.util.asNode(node1).id AS client1,
            gds.util.asNode(node2).id AS client2,similarity
        ORDER BY similarity;
        """
        self.conn.run_and_print_query(
            node_similarity_query,
            description="Node Similarity results (top 15 similar pairs)"
        )
        
        # Task 3: Mutate the in-memory graph with similarity results
        similarity_mutate_query = """
        CALL gds.nodeSimilarity.mutate('Similarity',{topK:15,
          mutateProperty:'jaccardScore', mutateRelationshipType:'SIMILAR_TO'});
        """
        self.conn.run_and_print_query(
            similarity_mutate_query,
            write=True,
            description="Mutating graph with similarity scores"
        )
        
        # Task 4: Write similarity relationships to the database
        write_similarity_query = """
        CALL gds.graph.writeRelationship('Similarity','SIMILAR_TO','jaccardScore');
        """
        self.conn.run_and_print_query(
            write_similarity_query,
            write=True,
            description="Writing SIMILAR_TO relationships to database"
        )
        
        # Task 5: Visualize similarity relationships
        visualize_similarity_query = """
        MATCH (c:Client)
        WITH c.firstPartyFraudGroup AS fpGroupID, collect(c.id) AS fGroup
        WITH *, size(fGroup) AS groupSize WHERE groupSize >= 9
        WITH collect(fpGroupID) AS fraudRings
        MATCH p=(c:Client)-[:SIMILAR_TO]->()
        WHERE c.firstPartyFraudGroup IN fraudRings
        RETURN p
        """
        print("\nTo visualize similarity relationships, run this query in Neo4j Browser:")
        print(visualize_similarity_query)
    
    def calculate_fraud_scores(self):
        """Calculate fraud scores based on centrality and label potential fraudsters"""
        print("\n=== Exercise 4: Calculating First-party Fraud Scores ===")
        
        # Task 1: Calculate degree centrality scores - using standard degree (not alpha)
        degree_centrality_query = """
        CALL gds.degree.stream('Similarity',{nodeLabels:['Client'],relationshipTypes:['SIMILAR_TO'],relationshipWeightProperty:'jaccardScore'})
        YIELD nodeId,score
        RETURN gds.util.asNode(nodeId).id AS client,score
        ORDER BY score DESC;
        """
        self.conn.run_and_print_query(
            degree_centrality_query,
            description="Degree Centrality scores (fraud scores)"
        )
        
        # Task 2: Write centrality scores to the database - using standard degree (not alpha)
        write_centrality_query = """
        CALL gds.degree.write('Similarity',{nodeLabels:['Client'],
            relationshipTypes:['SIMILAR_TO'],
            relationshipWeightProperty:'jaccardScore',
            writeProperty:'firstPartyFraudScore'});
        """
        self.conn.run_and_print_query(
            write_centrality_query,
            write=True,
            description="Writing fraud scores to database"
        )
        
        # Task 3: Label potential fraudsters - replaced exists() with IS NOT NULL
        label_fraudsters_query = """
        MATCH(c:Client)
        WHERE c.firstPartyFraudScore IS NOT NULL
        WITH percentileCont(c.firstPartyFraudScore, 0.8)
            AS firstPartyFraudThreshold
        MATCH(c:Client)
        WHERE c.firstPartyFraudScore>firstPartyFraudThreshold
        SET c:FirstPartyFraudster;
        """
        self.conn.run_and_print_query(
            label_fraudsters_query,
            write=True,
            description="Labeling potential fraudsters (scores above 80th percentile)"
        )
    
    def run_first_party_fraud_detection(self):
        """Run the complete first party fraud detection pipeline"""
        print("\n" + "="*80)
        print("MODULE 3: FIRST-PARTY FRAUD DETECTION".center(80))
        print("="*80)
        
        print("""
This module implements these steps:
1. Identifying clients sharing PII
2. Creating fraud rings using community detection (WCC)
3. Finding similar clients with Node Similarity
4. Calculating fraud scores with centrality algorithms
5. Identifying potential fraudsters
        """)
        
        try:
            # Step 1: Identify clients sharing PII
            self.identify_shared_pii()
            
            # Step 2: Detect fraud clusters
            self.detect_fraud_clusters()
            
            # Step 3: Find similar clients
            self.find_similar_clients()
            
            # Step 4: Calculate fraud scores
            self.calculate_fraud_scores()
            
            # Cleanup graphs (optional - comment out if you want to keep graphs)
            self.cleanup_graphs()
            
            print("\nEnd of Module 3: First-Party Fraud Detection")
            print(f"Successfully identified potential first-party fraudsters (label: FirstPartyFraudster)")
        
        except Exception as e:
            print(f"Error during first-party fraud detection: {e}")
            # Always try to clean up
            self.cleanup_graphs()

def main():
    """Main function to run the module"""
    conn = Neo4jConnection()
    try:
        detector = FirstPartyFraudDetection(conn)
        detector.run_first_party_fraud_detection()
    finally:
        conn.close()

if __name__ == "__main__":
    main() 