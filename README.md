# Graph Fraud Detection using Neo4j and Python

This project demonstrates how to use Neo4j, Graph Data Science (GDS), and Python to detect potential financial fraud, specifically focusing on first-party (synthetic identity) and second-party (money mule) fraud patterns within a simulated financial dataset (Paysim).

## Objective

The primary goal is to analyze connections within the Paysim dataset using graph technology to uncover suspicious patterns:

1.  **First-Party Fraud:** Identify clients potentially misrepresenting their identity by analyzing shared Personally Identifiable Information (PII) like SSN, Email, and Phone numbers. Clients sharing multiple identifiers form suspicious clusters (fraud rings).
2.  **Second-Party Fraud (Money Mules):** Identify accounts potentially used to transfer illicit funds by analyzing transaction patterns.

## Architecture Overview

The system relies on the following components:

1.  **Neo4j Database:** The core graph database storing nodes (Clients, Transactions, Merchants, PII) and their relationships.
2.  **Neo4j Graph Data Science (GDS) Plugin:** Used for efficient execution of graph algorithms (e.g., Weakly Connected Components, Node Similarity, PageRank) to identify fraud patterns.
3.  **APOC Plugin:** Provides utility functions for schema inspection, data statistics, and potentially complex data manipulations.
4.  **Data Files (`.dump`):** Pre-processed Paysim data ready for loading into Neo4j.
5.  **Cypher Scripts (`scripts/*.cypher`):** Contain queries for data loading, GDS algorithm execution, scoring, and result analysis.
6.  **Python Example (`code/python/example.py`):** Demonstrates how an external application can connect to Neo4j using the official Python driver to execute Cypher queries.
7.  **(Optional) Neo4j Bloom:** Used for interactive visual exploration of the graph and analysis results (requires `bloom/fraud-detection.bloom-perspective`).

**Data Flow:**

*   The Paysim dataset is loaded into Neo4j from a `.dump` file.
*   Cypher scripts are executed (often via Neo4j Browser or Bloom) to:
    *   Create `SHARED_IDENTIFIERS` relationships between clients sharing PII.
    *   Project relevant graph subsets into GDS.
    *   Run GDS algorithms (WCC, Node Similarity, PageRank, etc.).
    *   Write results (scores, component IDs) back to nodes.
*   The Python example (`code/python/example.py`) connects to the populated database to query specific results (e.g., clients associated with a particular merchant).
*   Neo4j Bloom can be used to visually explore the raw data and the results of the analysis.

## Core Data Model (Conceptual)

*   **Nodes:**
    *   `Client`: Represents individual customers.
    *   `Transaction`: Financial events (Payment, Transfer, etc.).
    *   `Merchant`: Entities receiving payments.
    *   `Email`, `Phone`, `SSN`: Personally Identifiable Information nodes.
*   **Relationships:**
    *   `(:Client)-[:PERFORMED]->(:Transaction)`
    *   `(:Transaction)-[:TO]->(:Merchant)`
    *   `(:Client)-[:HAS_EMAIL]->(:Email)`
    *   `(:Client)-[:HAS_PHONE]->(:Phone)`
    *   `(:Client)-[:HAS_SSN]->(:SSN)`
    *   **(Derived)** `(:Client)-[:SHARED_IDENTIFIERS]->(:Client)`
    *   **(Derived)** `(:Client)-[:SIMILAR]->(:Client)` (from GDS Node Similarity)

## Fraud Detection Concepts

*   **First-Party Fraud:** Clients linked by `SHARED_IDENTIFIERS` relationships form potential fraud rings. GDS Weakly Connected Components (WCC) algorithm helps identify these clusters. Scores might be derived from the size/density of these clusters or node similarity scores.
*   **Second-Party Fraud (Money Mules):** Transaction patterns are analyzed using algorithms like PageRank or community detection (Louvain, WCC) on the transaction graph to identify accounts primarily involved in funneling funds.

## Fraud Detection Implementation

The project uses a graph-based approach to detect two types of fraud:

### First-Party Fraud Detection (Synthetic Identity):
* The system identifies clients who share multiple pieces of personally identifiable information (PII) like email, phone, or SSN
* It creates `SHARED_IDENTIFIERS` relationships between these clients using the `sharedIdentifiers.cypher` script
* The Weakly Connected Components (WCC) algorithm groups these connected clients into clusters
* Clients in larger clusters are flagged as potential first-party fraudsters with a `firstPartyFraudScore`
* Clients with scores above the 80th percentile are labeled as `:FirstPartyFraudster`

### Second-Party Fraud Detection (Money Mules):
* The system analyzes transaction patterns between clients
* It uses PageRank algorithm to identify clients that function as hubs in transaction flows
* Transaction amounts are used as relationship weights in the algorithm
* Clients with high PageRank scores that aren't already identified as first-party fraudsters are labeled as `:SecondPartyFraud`

The Neo4j Graph Data Science (GDS) library is crucial to this implementation, allowing for:
* Creation of projected graphs for algorithm execution
* Running complex graph algorithms like WCC, PageRank, and Node Similarity
* Writing results back to the graph for visualization and querying

## Python Example (`code/python/example.py`)

This script demonstrates a basic interaction with the Neo4j database using the official Python driver.

*   **Purpose:** Connects to the database and executes a simple Cypher query to find clients who have transacted with a specific merchant (`MYrsa`).
*   **Dependencies:** Requires the `neo4j-driver` Python package.
    ```bash
    pip install neo4j-driver
    # Or potentially: python -m pip install neo4j-driver
    ```
*   **Configuration:** You need to update the script with your Neo4j instance details:
    *   `bolt://<HOST>:<BOLTPORT>`
    *   `<USERNAME>`
    *   `<PASSWORD>`
*   **Usage:**
    ```bash
    python code/python/example.py
    ```
    This will print the names of clients who performed transactions to the merchant "MYrsa".

## Running with Docker (Recommended)

Using Docker provides an isolated and reproducible environment for running Neo4j with the required plugins.

1.  **Prerequisites:** Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).
2.  **Configure:** Review `docker-compose.yml`. You may want to change the default password (`changeme`) in the `NEO4J_AUTH` environment variable.
3.  **Start Neo4j:** Open a terminal in the project root and run:
    ```bash
    docker-compose up -d
    ```
    The first time, this will download the Neo4j image and plugins.
4.  **Load Data:**
    *   Copy the appropriate `.dump` file (e.g., `data/fraud-detection-50.dump` for Neo4j 5.x) into the running container's import directory:
      ```bash
      docker cp data/fraud-detection-50.dump neo4j_fraud_detection:/var/lib/neo4j/import/fraud-detection-50.dump
      ```
    *   Stop Neo4j cleanly:
      ```bash
      docker-compose stop neo4j
      ```
    *   Execute the load command:
      ```bash
      docker exec neo4j_fraud_detection neo4j-admin database load --from-path=/var/lib/neo4j/import/fraud-detection-50.dump neo4j --overwrite-destination=true
      ```
    *   Restart Neo4j:
      ```bash
      docker-compose start neo4j
      ```
5.  **Access Neo4j:** Open the Neo4j Browser at `http://localhost:7474`. Log in with user `neo4j` and the password you set (default: `changeme`).
6.  **Run Python Script:**
    *   Install the driver: `pip install neo4j-driver`
    *   Edit `code/python/neo4j_query_example.py` and set the connection details:
        *   HOST: `localhost`
        *   BOLTPORT: `7687`
        *   USERNAME: `neo4j`
        *   PASSWORD: The password set in `docker-compose.yml` (default: `changeme`).
    *   Execute: `python code/python/neo4j_query_example.py`
7.  **Stop Neo4j:**
    ```bash
    docker-compose down
    ```
    This stops and removes the container but preserves the data in the `./neo4j/data` directory.

## Setup and Usage (Manual Installation)

If you prefer not to use Docker, follow these steps:

1.  **Install Neo4j:** Set up a Neo4j Server instance (versions 3.5, 4.x, or 5.x are supported by the provided dumps).
2.  **Install Plugins:** Install the Neo4j Graph Data Science (GDS) and APOC library plugins compatible with your Neo4j version.
3.  **Load Data:**
    * Dump the data using below command 
    "docker cp data/fraud-detection-50.dump neo4j_fraud_detection:/var/lib/neo4j/import/fraud-detection-50.dump" 
    *   Choose the `.dump` file from the `data/` directory that matches your Neo4j version (e.g., `data/fraud-detection-50.dump` for Neo4j 5.x).
    *   Load the dump using `neo4j-admin load`, Neo4j Desktop, or the Neo4j Aura console.
4.  **Start Neo4j:** Ensure your Neo4j database instance is running.
5.  **Install Python Driver:** Install the necessary Python package:
    ```bash
    pip install neo4j-driver
    ```
6.  **Configure Python Script:** Edit `code/python/example.py` and replace the placeholder `<HOST>`, `<BOLTPORT>`, `<USERNAME>`, and `<PASSWORD>` with your actual Neo4j connection details.
7.  **Run Python Script:**
    ```bash
    python code/python/example.py
    ```

## Full Analysis & Visualization

For the complete fraud detection analysis involving GDS algorithms and scoring, refer to the Cypher scripts located in the `scripts/` directory. These are typically run via the Neo4j Browser.

For interactive visual exploration, use Neo4j Bloom and import the perspective file `bloom/fraud-detection.bloom-perspective`. 