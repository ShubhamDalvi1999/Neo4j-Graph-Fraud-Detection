#!/usr/bin/env python3
"""
Module 2: Preliminary Data Analysis - Graph Fraud Detection

This module provides functionality to explore and analyze the fraud detection dataset.
"""

import os
import sys
# Ensure the neo4j_connection module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from neo4j_connection import Neo4jConnection

class DataAnalysis:
    """Class for performing preliminary data analysis on Neo4j graph data"""
    
    def __init__(self, connection):
        """Initialize with a Neo4j connection
        
        Args:
            connection (Neo4jConnection): An established Neo4j connection
        """
        self.conn = connection
    
    def get_database_schema(self):
        """Get the database schema visualization query
        
        Note: This query can only be executed in Neo4j Browser
        """
        schema_query = "CALL db.schema.visualization();"
        print("\nTo visualize the database schema, run this query in Neo4j Browser:")
        print(schema_query)
        return schema_query
    
    def get_database_stats(self):
        """Get and print overall database statistics using APOC"""
        stats_query = """
        CALL apoc.meta.stats();
        """
        return self.conn.run_and_print_query(
            stats_query, 
            description="Database Statistics (using APOC)")
    
    def get_node_labels(self):
        """Get statistics on node labels in the database"""
        labels_query = """
        CALL db.labels() YIELD label
        CALL apoc.cypher.run('MATCH (:`'+label+'`) RETURN count(*) as freq',{})
        YIELD value
        WITH label,value.freq AS freq
        CALL apoc.meta.stats() YIELD nodeCount
        WITH *,3 AS presicion
        WITH *,10^presicion AS factor,toFloat(freq)/toFloat(nodeCount) AS relFreq
        RETURN label AS nodeLabel, freq AS frequency,round(relFreq*factor)/factor AS relativeFrequency 
        ORDER BY freq DESC;
        """
        return self.conn.run_and_print_query(
            labels_query, 
            description="Node Label Statistics")
    
    def get_relationship_types(self):
        """Get statistics on relationship types in the database"""
        rel_query = """
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
        """
        return self.conn.run_and_print_query(
            rel_query, 
            description="Relationship Type Statistics")
    
    def get_property_metadata(self):
        """Get metadata about node and relationship properties"""
        props_query = """
        CALL apoc.meta.data() YIELD label,property,type,elementType
        WHERE type<>'RELATIONSHIP'
        RETURN elementType,label,property,type
        ORDER BY elementType,label,property;
        """
        return self.conn.run_and_print_query(
            props_query, 
            description="Node and Relationship Properties")
    
    def get_transaction_types(self):
        """Get statistics on different transaction types"""
        tx_query = """
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
        """
        return self.conn.run_and_print_query(
            tx_query, 
            description="Transaction Type Statistics")
    
    def run_all_analyses(self):
        """Run all data analysis queries in sequence"""
        print("\n" + "="*80)
        print("MODULE 2: PRELIMINARY DATA ANALYSIS".center(80))
        print("="*80)
        
        print("\nThis module explores the dataset and collects statistics on:")
        print(" - Database schema and size")
        print(" - Node labels and relationship types distributions")
        print(" - Node and relationship properties")
        print(" - Transaction type distribution")
        
        self.get_database_schema()
        self.get_database_stats()
        self.get_node_labels()
        self.get_relationship_types()
        self.get_property_metadata()
        self.get_transaction_types()
        
        print("\nEnd of Module 2: Preliminary Data Analysis")

def main():
    """Main function to run the module"""
    conn = Neo4jConnection()
    try:
        analyzer = DataAnalysis(conn)
        analyzer.run_all_analyses()
    finally:
        conn.close()

if __name__ == "__main__":
    main() 