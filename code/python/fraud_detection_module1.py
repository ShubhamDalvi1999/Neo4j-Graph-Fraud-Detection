#!/usr/bin/env python3
"""
Module 1: Problem Definition - Graph Fraud Detection

This module provides documentation on fraud types and categories in the context
of graph-based fraud detection.
"""

class FraudDefinitions:
    """Class containing descriptions and definitions of fraud types"""
    
    @staticmethod
    def get_fraud_definition():
        """Returns the general definition of fraud"""
        return """
        What is Fraud?
        --------------
        Fraud occurs when an individual or group of individuals, or a business entity 
        intentionally deceives another individual or business entity with misrepresentation 
        of identity, products, services, or financial transactions and/or false promises 
        with no intention of fulfilling them.
        """
    
    @staticmethod
    def get_fraud_categories():
        """Returns descriptions of the three main fraud categories"""
        return """
        Fraud Categories
        ---------------
        First-party Fraud:
        An individual, or group of individuals, misrepresent their identity or give 
        false information when applying for a product or services to receive more 
        favorable rates or when have no intention of repayment.

        Second-party Fraud:
        An individual knowingly gives their identity or personal information to 
        another individual to commit fraud or someone is perpetrating fraud in 
        his behalf.

        Third-party Fraud:
        An individual, or group of individuals, create or use another person's 
        identity, or personal details, to open or takeover an account.
        """

def print_module_info():
    """Print information about this module"""
    print("\n" + "="*80)
    print("MODULE 1: PROBLEM DEFINITION".center(80))
    print("="*80)
    
    fraud_defs = FraudDefinitions()
    print(fraud_defs.get_fraud_definition())
    print(fraud_defs.get_fraud_categories())
    
    print("""
    In this analysis, we will focus on detecting two main types of fraud:
    
    1. First-party fraud - Using graph algorithms to detect clusters of 
       synthetic identities sharing personally identifiable information (PII)
    
    2. Second-party fraud - Using graph algorithms to identify money mules
       based on transaction patterns with first-party fraudsters
    """)

if __name__ == "__main__":
    print_module_info() 