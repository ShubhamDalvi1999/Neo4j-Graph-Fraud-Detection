// ============================================================================
// MODULE 1: PROBLEM DEFINITION - GRAPH FRAUD DETECTION
// ============================================================================

// What is Fraud?
// --------------
// Fraud occurs when an individual or group of individuals, or a business entity 
// intentionally deceives another individual or business entity with misrepresentation 
// of identity, products, services, or financial transactions and/or false promises 
// with no intention of fulfilling them.

// Fraud Categories
// ---------------
// First-party Fraud:
// An individual, or group of individuals, misrepresent their identity or give 
// false information when applying for a product or services to receive more 
// favorable rates or when have no intention of repayment.

// Second-party Fraud:
// An individual knowingly gives their identity or personal information to 
// another individual to commit fraud or someone is perpetrating fraud in 
// his behalf.

// Third-party Fraud:
// An individual, or group of individuals, create or use another person's 
// identity, or personal details, to open or takeover an account.

// In this analysis, we will focus on detecting two main types of fraud:
//
// 1. First-party fraud - Using graph algorithms to detect clusters of 
//    synthetic identities sharing personally identifiable information (PII)
//
// 2. Second-party fraud - Using graph algorithms to identify money mules
//    based on transaction patterns with first-party fraudsters 