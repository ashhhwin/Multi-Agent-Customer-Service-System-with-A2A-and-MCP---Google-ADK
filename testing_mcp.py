"""
direct_db_query.py: Standalone script to test MCP tools and database access directly.

This script executes a tool function synchronously and prints the raw JSON output, 
bypassing all LLM and A2A components to prove database and tool functionality.
"""
import sys
import os
import time

# --- Database Initialization (Required) ---
try:
    # We must ensure the database is created and seeded by running the initialization function
    from mcp_server import initialize_database_schema
    initialize_database_schema()
    print("Database initialized and seeded.")
except ImportError:
    print("FATAL: Could not import initialize_database_schema. Ensure 'mcp_server.py' is in the directory.")
    sys.exit(1)

# --- MCP Tool Imports ---
try:
    # Import the actual MCP tool functions we want to test
    from service_tools import fetch_customer_data, register_support_issue
except ImportError:
    print("FATAL: Could not import tool functions from service_tools.py. Check function names.")
    sys.exit(1)


def run_direct_query_test(description: str, tool_function: callable, **kwargs):
    """Executes a specific MCP tool function and prints the result."""
    
    print("\n" + "="*50)
    print(f"TEST: {description}")
    print(f"Tool: {tool_function.__name__}")
    print(f"Params: {kwargs}")
    print("="*50)

    try:
        # Execute the synchronous function that calls the MCP server logic
        raw_output = tool_function(**kwargs)
        
        print("\n✅ RAW MCP OUTPUT (DB Data):")
        print(raw_output)
        
    except Exception as e:
        print(f"\n❌ ERROR EXECUTING TOOL:")
        print(str(e))


if __name__ == "__main__":
    
    # 1. Test Customer Data Retrieval (SELECT query)
    run_direct_query_test(
        "Retrieve Details for Customer ID 2",
        fetch_customer_data,
        customer_id=2
    )

    # 2. Test Ticket Creation (INSERT query)
    # Note: This will create a new ticket in the database.
    run_direct_query_test(
        "Create New High-Priority Ticket for Customer 3",
        register_support_issue,
        customer_id=3,
        query_description="Account status incorrectly set to disabled.",
        urgency_level="high"
    )

    print("\n--- Direct Tool Testing Complete ---")