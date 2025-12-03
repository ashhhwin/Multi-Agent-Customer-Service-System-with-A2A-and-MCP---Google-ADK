"""
mcp_server.py: Microservice Communication Protocol (MCP) Backend
This service provides an HTTP API layer over the SQLite database, 
allowing agents to perform CRUD operations via well-defined tools.
"""
import sqlite3
import datetime
import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

DB_FILENAME = "service_db.sqlite"

def get_threadsafe_db_connector():
    """Establishes a thread-safe connection to the SQLite database."""
    connector = sqlite3.connect(DB_FILENAME, check_same_thread=False)
    connector.row_factory = sqlite3.Row # Allows column access by name
    return connector

# This initialization function is needed if the MCP server is run first.
def initialize_database_schema():
    """Sets up and seeds the customer and ticket tables for the server's use."""
    connector = get_threadsafe_db_connector()
    cursor = connector.cursor()
    
    # Reset tables to match the original deterministic seeding logic
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DROP TABLE IF EXISTS support_tickets;")
    cursor.execute("DROP TABLE IF EXISTS customer_accounts;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create customer_accounts table
    cursor.execute("""
        CREATE TABLE customer_accounts (
            identifier INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            account_status TEXT,
            creation_timestamp TEXT,
            last_modified_timestamp TEXT
        )""")
    # Create support_tickets table
    cursor.execute("""
        CREATE TABLE support_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            description TEXT,
            status TEXT,
            priority_level TEXT,
            submission_timestamp TEXT
        )""")
    connector.commit()
    
    # Insert seed data
    current_utc = datetime.datetime.now(datetime.UTC).isoformat()
    account_data = [
        (1, "Alice Premium", "alice@example.com", "111-111-1111", "active", current_utc, current_utc),
        (2, "Bob Standard", "bob@example.com", "222-222-2222", "active", current_utc, current_utc),
        (3, "Charlie Disabled", "charlie@example.com", "333-333-3333", "disabled", current_utc, current_utc),
        (4, "Diana Premium", "diana@example.com", "444-444-4444", "active", current_utc, current_utc),
        (5, "Eve Standard", "eve@example.com", "555-555-5555", "active", current_utc, current_utc),
        (12345, "Priya Patel (Premium)", "priya@example.com", "555-0999", "active", current_utc, current_utc),
    ]
    cursor.executemany(
        "INSERT INTO customer_accounts (identifier, full_name, contact_email, contact_phone, account_status, creation_timestamp, last_modified_timestamp) VALUES (?,?,?,?,?,?,?)",
        account_data
    )
    ticket_data = [
        (1, "Billing duplicate charge", "open", "high", current_utc),
        (1, "Unable to login", "in_progress", "medium", current_utc),
        (2, "Request upgrade", "open", "low", current_utc),
        (4, "Critical outage", "open", "high", current_utc),
        (5, "Password reset", "open", "low", current_utc),
        (12345, "Account upgrade assistance", "open", "medium", current_utc),
        (12345, "High priority refund review", "open", "high", current_utc),
    ]
    cursor.executemany(
        "INSERT INTO support_tickets (account_id, description, status, priority_level, submission_timestamp) VALUES (?,?,?,?,?)",
        ticket_data
    )
    connector.commit()
    print(f"Database schema initialized and seeded at {DB_FILENAME}")
    connector.close()


class DataAccessService:
    """Manages the callable database operations (tools)."""
    
    def __init__(self):
        self.operations = {
            "get_customer": self._fetch_customer_record,
            "list_customers": self._search_customer_records,
            "update_customer": self._modify_customer_details,
            "create_ticket": self._register_new_ticket,
            "get_customer_history": self._retrieve_ticket_history,
        }
    
    async def _fetch_customer_record(self, customer_id: int):
        """MCP operation: Retrieve customer by ID."""
        conn = get_threadsafe_db_connector()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_accounts WHERE identifier=?", (customer_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"success": True, "data": dict(row)}
        return {"success": False, "error": f"Account with ID {customer_id} not found"}
    
    async def _search_customer_records(self, status: str = None, limit: int = 100):
        """MCP operation: List accounts, optionally filtered by status."""
        conn = get_threadsafe_db_connector()
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM customer_accounts WHERE account_status=? LIMIT ?", (status, limit))
        else:
            cursor.execute("SELECT * FROM customer_accounts LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return {"success": True, "data": [dict(r) for r in rows], "total_count": len(rows)}
    
    async def _modify_customer_details(self, customer_id: int, data: dict):
        """MCP operation: Update specific customer fields."""
        conn = get_threadsafe_db_connector()
        cursor = conn.cursor()
        
        # Build update query (paraphrased column names)
        valid_fields = ["full_name", "contact_email", "contact_phone", "account_status"]
        updates = {k: v for k, v in data.items() if k in valid_fields}
        
        if not updates:
            conn.close()
            return {"success": False, "error": "No valid fields provided for update."}
        
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        params = list(updates.values()) + [datetime.datetime.now(datetime.UTC).isoformat(), customer_id]
        
        cursor.execute(
            f"UPDATE customer_accounts SET {set_clause}, last_modified_timestamp=? WHERE identifier=?", 
            params
        )
        conn.commit()
        
        # Fetch and return updated record
        cursor.execute("SELECT * FROM customer_accounts WHERE identifier=?", (customer_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"success": True, "data": dict(row)}
        return {"success": False, "error": f"Account {customer_id} not found or update failed."}
    
    async def _register_new_ticket(self, customer_id: int, issue: str, priority: str = "medium"):
        """MCP operation: Create a new support ticket."""
        conn = get_threadsafe_db_connector()
        cursor = conn.cursor()
        
        normalized_priority = priority.lower()
        if normalized_priority not in ["low", "medium", "high"]:
            conn.close()
            return {"success": False, "error": "Priority must be 'low', 'medium', or 'high'."}
        
        current_utc = datetime.datetime.now(datetime.UTC).isoformat()
        cursor.execute(
            "INSERT INTO support_tickets (account_id, description, status, priority_level, submission_timestamp) VALUES (?, ?, ?, ?, ?)",
            (customer_id, issue, "open", normalized_priority, current_utc)
        )
        conn.commit()
        new_ticket_id = cursor.lastrowid
        cursor.execute("SELECT * FROM support_tickets WHERE ticket_id=?", (new_ticket_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {"success": True, "data": dict(row)}
        return {"success": False, "error": "Database error: Failed to log new ticket."}
    
    async def _retrieve_ticket_history(self, customer_id: int):
        """MCP operation: Get all tickets for a customer ID."""
        conn = get_threadsafe_db_connector()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM support_tickets WHERE account_id=? ORDER BY submission_timestamp DESC",
            (customer_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return {"success": True, "data": [dict(r) for r in rows], "total_count": len(rows)}
    
    async def execute_operation(self, operation_name: str, **kwargs):
        """Executes a database operation by name."""
        if operation_name not in self.operations:
            return {"success": False, "error": f"Unknown database operation: {operation_name}"}
        try:
            # Execute the async method
            return await self.operations[operation_name](**kwargs)
        except Exception as e:
            # Catch execution errors within the tool logic
            return {"success": False, "error": f"Operation execution failed: {type(e).__name__} - {str(e)}"}


# Create the service instance
data_service = DataAccessService()

# HTTP Handlers for the Starlette Application
async def list_available_tools_handler(request):
    """GET /tools: Provides documentation for available operations."""
    # Note: Using the exact same tool names as the original file for functional parity
    tool_list = [
        {"name": "get_customer", "description": "Retrieve customer account by ID.", "parameters": {"customer_id": "integer"}},
        {"name": "list_customers", "description": "Search accounts, optionally filtered by status.", "parameters": {"status": "string (optional)", "limit": "integer (optional)"}},
        {"name": "update_customer", "description": "Modify customer record details.", "parameters": {"customer_id": "integer", "data": "JSON object of fields to update"}},
        {"name": "create_ticket", "description": "Log a new support ticket.", "parameters": {"customer_id": "integer", "issue": "string", "priority": "string (low/medium/high)"}},
        {"name": "get_customer_history", "description": "Get all historical tickets for an account.", "parameters": {"customer_id": "integer"}},
    ]
    return JSONResponse({"available_operations": tool_list})


async def call_operation_handler(request):
    """POST /call: Executes a named operation with parameters."""
    try:
        request_body = await request.json()
        op_name = request_body.get("tool")
        op_params = request_body.get("params", {})
        
        # Delegate to the DataAccessService
        result = await data_service.execute_operation(op_name, **op_params)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"Invalid request format: {str(e)}"}, status_code=400)


# Define the Starlette application routes
mcp_api_app = Starlette(routes=[
    Route("/tools", list_available_tools_handler, methods=["GET"]),
    Route("/call", call_operation_handler, methods=["POST"]),
])

# Utility function to run the server for main.py
async def run_mcp_server_async():
    """Configures and runs the MCP Starlette server."""
    print("Initializing MCP Data Server...")
    initialize_database_schema()
    
    server_config = uvicorn.Config(
        mcp_api_app,
        host="127.0.0.1",
        port=8000,
        log_level="warning" # Set lower log level to reduce console noise
    )
    server_instance = uvicorn.Server(server_config)
    print("\n[MCP READY] Data Access Server listening on http://127.0.0.1:8000")
    await server_instance.serve()

if __name__ == "__main__":
    # We must import asyncio to use asyncio.run()
    import asyncio 
    
    # run_mcp_server_async contains the initialization and the uvicorn.Server(config).serve() call.
    print("\nStarting MCP Server on http://127.0.0.1:8000")
    print("Press Ctrl+C to stop\n")
    
    # Execute the asynchronous server startup function
    asyncio.run(run_mcp_server_async())