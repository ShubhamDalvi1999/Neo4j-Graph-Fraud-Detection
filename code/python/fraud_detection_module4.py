#!/usr/bin/env python3
"""
Module 4: Second-party Fraud Detection - Graph Fraud Detection

This module implements the detection of second-party fraud (money mules) using graph algorithms.
Steps include:
1. Identifying transactions between first-party fraudsters and other clients
2. Creating transfer relationship networks
3. Detecting fraud networks using PageRank
4. Labeling potential second-party fraudsters
"""

import os
import sys
# Ensure the neo4j_connection module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from neo4j_connection import Neo4jConnection

class SecondPartyFraudDetection:
    """Class implementing second-party fraud detection using Neo4j GDS"""
    
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
        
        # Check if first-party fraud detection has been run
        first_party_check = self.conn.execute_query(
            "MATCH (c:Client:FirstPartyFraudster) RETURN count(c) AS fraudsterCount"
        )
        
        if not first_party_check or first_party_check[0]['fraudsterCount'] == 0:
            raise RuntimeError("First-party fraud detection (Module 3) must be run before second-party fraud detection")
        
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
    
    def identify_transactions(self):
        """Identify transactions between first-party fraudsters and other clients"""
        print("\n=== Exercise 1: Identifying Transactions Between Fraudsters and Clients ===")
        
        # Task 1: Find transactions between fraudsters and non-fraudsters
        fraudster_transactions_query = """
        MATCH p=(:Client:FirstPartyFraudster)-[]-(:Transaction)-[]-(c:Client)
        WHERE NOT c:FirstPartyFraudster
        RETURN p LIMIT 10;
        """
        print("\nTo visualize transactions between fraudsters and non-fraudsters, run this query in Neo4j Browser:")
        print(fraudster_transactions_query)
        
        # Find transaction types
        transaction_types_query = """
        MATCH (:Client:FirstPartyFraudster)-[]-(txn:Transaction)-[]-(c:Client)
        WHERE NOT c:FirstPartyFraudster
        UNWIND labels(txn) AS transactionType
        RETURN transactionType, count(*) AS freq;
        """
        self.conn.run_and_print_query(
            transaction_types_query,
            description="Transaction types between fraudsters and non-fraudsters"
        )
        
        # Task 2: Create TRANSFER_TO relationships from fraudsters to clients
        create_transfer_to_query1 = """
        MATCH (c1:Client:FirstPartyFraudster)-[]->(t:Transaction)-[]->(c2:Client)
        WHERE NOT c2:FirstPartyFraudster
        WITH c1,c2,sum(t.amount) AS totalAmount
        SET c2:SecondPartyFraudSuspect
        CREATE (c1)-[:TRANSFER_TO {amount:totalAmount}]->(c2);
        """
        self.conn.run_and_print_query(
            create_transfer_to_query1,
            write=True,
            description="Creating TRANSFER_TO relationships (fraudster to client)"
        )
        
        # Create TRANSFER_TO relationships from clients to fraudsters
        create_transfer_to_query2 = """
        MATCH (c1:Client:FirstPartyFraudster)<-[]-(t:Transaction)<-[]-(c2:Client)
        WITH c1,c2,sum(t.amount) AS totalAmount
        CREATE (c1)<-[:TRANSFER_TO {amount:totalAmount}]-(c2);
        """
        self.conn.run_and_print_query(
            create_transfer_to_query2,
            write=True,
            description="Creating TRANSFER_TO relationships (client to fraudster)"
        )
        
        # Task 3: Visualize TRANSFER_TO relationships
        visualize_transfers_query = """
        MATCH p=(:Client:FirstPartyFraudster)-[:TRANSFER_TO]-(c:Client)
        WHERE NOT c:FirstPartyFraudster
        RETURN p LIMIT 25;
        """
        print("\nTo visualize TRANSFER_TO relationships, run this query in Neo4j Browser:")
        print(visualize_transfers_query)
    
    def detect_second_party_fraud(self):
        """Detect second-party fraud using community detection and PageRank"""
        print("\n=== Exercise 2: Detecting Second-party Fraud ===")
        
        # Task 1: Create an in-memory graph - first drop if exists
        self.drop_existing_graph('SecondPartyFraudNetwork')
        
        create_graph_query = """
        CALL gds.graph.project('SecondPartyFraudNetwork','Client','TRANSFER_TO',
            {relationshipProperties:'amount'});
        """
        result = self.conn.run_and_print_query(
            create_graph_query,
            write=True,
            description="Creating graph for second-party fraud detection"
        )
        
        if result:
            self.graph_names.append('SecondPartyFraudNetwork')
        
        # Task 2: Execute WCC to find clusters - stream results
        wcc_stream_query = """
        CALL gds.wcc.stream('SecondPartyFraudNetwork')
        YIELD nodeId,componentId
        WITH gds.util.asNode(nodeId) AS client,componentId AS clusterId
        WITH clusterId,collect(client.id) AS cluster
        WITH clusterId,size(cluster) AS clusterSize,cluster
        WHERE clusterSize>1
        RETURN clusterId,clusterSize
        ORDER BY clusterSize DESC;
        """
        self.conn.run_and_print_query(
            wcc_stream_query,
            description="WCC clusters (potential fraud networks)"
        )
        
        # Write WCC results to the database
        wcc_write_query = """
        CALL gds.wcc.stream('SecondPartyFraudNetwork')
        YIELD nodeId,componentId
        WITH gds.util.asNode(nodeId) AS client,componentId AS clusterId
        WITH clusterId,collect(client.id) AS cluster
        WITH clusterId,size(cluster) AS clusterSize,cluster
        WHERE clusterSize>1
        UNWIND cluster AS client
        MATCH(c:Client {id:client})
        SET c.secondPartyFraudGroup=clusterId;
        """
        self.conn.run_and_print_query(
            wcc_write_query,
            write=True,
            description="Writing fraud network clusters to database"
        )
        
        # Task 3: Identify second-party fraudsters using PageRank - stream results
        pagerank_stream_query = """
        CALL gds.pageRank.stream('SecondPartyFraudNetwork',
            {relationshipWeightProperty:'amount'})
        YIELD nodeId,score
        WITH gds.util.asNode(nodeId) AS client,score AS pageRankScore
        WHERE client.secondPartyFraudGroup IS NOT NULL
        RETURN client.secondPartyFraudGroup,client.name,labels(client),pageRankScore
        ORDER BY client.secondPartyFraudGroup,pageRankScore DESC;
        """
        self.conn.run_and_print_query(
            pagerank_stream_query,
            description="PageRank scores (by fraud group)"
        )
        
        # Write PageRank results to the database and label second-party fraudsters
        pagerank_write_query = """
        CALL gds.pageRank.stream('SecondPartyFraudNetwork',
            {relationshipWeightProperty:'amount'})
        YIELD nodeId,score
        WITH gds.util.asNode(nodeId) AS client,score AS pageRankScore
        WHERE client.secondPartyFraudGroup IS NOT NULL
            AND pageRankScore >1 AND NOT client:FirstPartyFraudster
        MATCH(c:Client {id:client.id})
        SET c:SecondPartyFraud
        SET c.secondPartyFraudScore=pageRankScore;
        """
        self.conn.run_and_print_query(
            pagerank_write_query,
            write=True,
            description="Labeling second-party fraudsters"
        )
        
        # Task 4: Visualize second-party fraud networks
        visualize_networks_query = """
        MATCH p=(:Client:FirstPartyFraudster)-[:TRANSFER_TO]-(c:Client:SecondPartyFraud)
        RETURN p;
        """
        print("\nTo visualize second-party fraud networks, run this query in Neo4j Browser:")
        print(visualize_networks_query)
    
    def run_second_party_fraud_detection(self):
        """Run the complete second-party fraud detection pipeline"""
        print("\n" + "="*80)
        print("MODULE 4: SECOND-PARTY FRAUD DETECTION".center(80))
        print("="*80)
        
        print("""
This module implements these steps:
1. Identifying transactions between first-party fraudsters and other clients
2. Creating transfer relationship networks
3. Detecting fraud networks using community detection and PageRank
4. Labeling potential second-party fraudsters
        """)
        
        try:
            # Step 1: Identify transactions
            self.identify_transactions()
            
            # Step 2: Detect second-party fraud
            self.detect_second_party_fraud()
            
            # Cleanup graphs
            self.cleanup_graphs()
            
            # Get counts of identified fraudsters
            first_party_count = self.conn.execute_query(
                "MATCH (c:Client:FirstPartyFraudster) RETURN count(c) AS count"
            )
            second_party_count = self.conn.execute_query(
                "MATCH (c:Client:SecondPartyFraud) RETURN count(c) AS count"
            )
            
            fp_count = first_party_count[0]['count'] if first_party_count else 0
            sp_count = second_party_count[0]['count'] if second_party_count else 0
            
            print("\nEnd of Module 4: Second-Party Fraud Detection")
            print(f"Successfully identified {fp_count} first-party fraudsters and {sp_count} second-party fraudsters")
            
            # Provide visualization query for all identified fraudsters
            final_visualization = """
            MATCH p=(f1:Client:FirstPartyFraudster)-[:TRANSFER_TO]-(f2:Client:SecondPartyFraud)
            RETURN p LIMIT 100;
            """
            print("\nTo visualize all identified fraudsters and their connections, run:")
            print(final_visualization)
        
        except Exception as e:
            print(f"Error during second-party fraud detection: {e}")
            # Always try to clean up
            self.cleanup_graphs()
            
def main():
    """Main function to run the module"""
    conn = Neo4jConnection()
    try:
        detector = SecondPartyFraudDetection(conn)
        detector.run_second_party_fraud_detection()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("\nYou must run Module 3 (First-party Fraud Detection) before running Module 4")
    finally:
        conn.close()

if __name__ == "__main__":
    main() 