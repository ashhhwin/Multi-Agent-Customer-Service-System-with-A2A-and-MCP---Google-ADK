import httpx
import asyncio
import json
from typing import Optional, List

MCP_ACCESS_SERVER_URL = "http://127.0.0.1:8000"

async def _execute_mcp_operation_async(operation_name: str, **parameters) -> str:
    """Async version of MCP operation execution with longer timeout."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{MCP_ACCESS_SERVER_URL}/call",
                json={"tool": operation_name, "params": parameters}
            )
            response.raise_for_status()
            operation_result = response.json()
            
            if operation_result.get("success"):
                returned_data = operation_result.get("data")
                if isinstance(returned_data, (dict, list)):
                    return json.dumps(returned_data, indent=2)
                return str(returned_data)
            else:
                return f"Operation Error: {operation_result.get('error', 'Unknown service error')}"
    except Exception as e:
        return f"Service Execution Failure: {str(e)}"

def _execute_mcp_operation(operation_name: str, **parameters) -> str:
    """Synchronous wrapper that runs async operation in event loop."""
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(_execute_mcp_operation_async(operation_name, **parameters))
        else:
            return loop.run_until_complete(_execute_mcp_operation_async(operation_name, **parameters))
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(_execute_mcp_operation_async(operation_name, **parameters))

def fetch_customer_data(customer_id: int) -> str:
    """Retrieve customer account details by ID."""
    return _execute_mcp_operation("get_customer", customer_id=customer_id)

def search_customer_accounts(account_status: Optional[str] = None, result_limit: int = 10) -> str:
    """Search for customer accounts, optionally filtered by status."""
    parameters = {"limit": result_limit}
    if account_status:
        parameters["status"] = account_status
    return _execute_mcp_operation("list_customers", **parameters)

def modify_customer_record(customer_id: int, update_payload: str) -> str:
    """Update customer record fields."""
    try:
        payload_dict = json.loads(update_payload)
    except json.JSONDecodeError:
        return "Parsing Error: The provided data for update must be a valid JSON string."
    return _execute_mcp_operation("update_customer", customer_id=customer_id, data=payload_dict)

def register_support_issue(customer_id: int, query_description: str, urgency_level: str = "medium") -> str:
    """Create a new support ticket."""
    return _execute_mcp_operation("create_ticket", customer_id=customer_id, issue=query_description, priority=urgency_level)

def retrieve_customer_history(customer_id: int) -> str:
    """Get all support tickets for a customer."""
    return _execute_mcp_operation("get_customer_history", customer_id=customer_id)

def generate_agent_tools() -> List[callable]:
    """Generate list of tool functions for agents."""
    return [
        fetch_customer_data,
        search_customer_accounts,
        modify_customer_record,
        register_support_issue,
        retrieve_customer_history,
    ]

AGENT_TOOLS = generate_agent_tools()