"""
client_runner.py: A2A Test Client and Scenario Executor
Defines a client utility to communicate with the deployed A2A agents and runs 
a suite of tests against the Orchestration Agent.
"""
import httpx
import asyncio
from a2a.client import ClientConfig, ClientFactory, create_text_message_object
from a2a.types import AgentCard, TransportProtocol
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

class CommunicationClient:
    """Client utility for sending messages to A2A endpoints."""
    
    def __init__(self, request_timeout: float = 240.0):
        self._agent_metadata_cache: dict[str, dict | None] = {}
        self.request_timeout = request_timeout
    
    async def dispatch_message(self, agent_endpoint_url: str, content: str) -> str:
        """Sends a message and returns the final text response."""
        
        timeout_settings = httpx.Timeout(
            timeout=self.request_timeout,
            connect=10.0,
            read=self.request_timeout,
            write=10.0,
            pool=5.0,
        )
        
        async with httpx.AsyncClient(timeout=timeout_settings) as http_client:
            
            if agent_endpoint_url not in self._agent_metadata_cache:
                metadata_url = f'{agent_endpoint_url}{AGENT_CARD_WELL_KNOWN_PATH}'
                metadata_response = await http_client.get(metadata_url)
                metadata_response.raise_for_status()
                self._agent_metadata_cache[agent_endpoint_url] = metadata_response.json()
            
            metadata = self._agent_metadata_cache[agent_endpoint_url]
            agent_card_object = AgentCard(**metadata)
            
            client_config = ClientConfig(
                httpx_client=http_client,
                supported_transports=[TransportProtocol.jsonrpc], 
                use_client_preference=True,
            )
            
            factory = ClientFactory(client_config)
            agent_client = factory.create(agent_card_object)
            
            message_body = create_text_message_object(content=content)
            
            response_chunks = []
            async for response in agent_client.send_message(message_body):
                response_chunks.append(response)
            
            if (response_chunks and isinstance(response_chunks[0], tuple) and len(response_chunks[0]) > 0):
                task = response_chunks[0][0]
                try:
                    return task.artifacts[0].parts[0].root.text
                except (AttributeError, IndexError):
                    return f"Received task object but could not extract text: {str(task)}"
            
            return 'No communication response received from agent.'

# ============================================================================
# TEST SCENARIOS
# ============================================================================

async def execute_test_suite():
    """Runs a predefined suite of integration tests against the Orchestration Agent."""
    test_comms_client = CommunicationClient(request_timeout=90.0)
    orchestrator_url = "http://127.0.0.1:9400"

    print("\n" + "="*80)
    print("INTEGRATION TEST SUITE - Multi-Agent Service System")
    print("="*80)

    test_cases = [
        {
            "name": "CASE 1: Simple Data Retrieval",
            "message": "Please get the full record for customer ID 1",
            "notes": "Routes to Information Agent for a basic lookup.",
            "expected": "Should return full customer record with all fields"
        },
        {
            "name": "CASE 2: Coordinated Service Request",
            "message": "I am customer ID 2 and I need to upgrade my service plan to Premium.",
            "notes": "Router should delegate to Support Agent to create an upgrade ticket.",
            "expected": "Should create a support ticket for service upgrade request"
        },
        {
            "name": "CASE 3: Complex Filtering Query",
            "message": "Show me all active customer accounts that have open support tickets.",
            "notes": "Requires multiple tool calls: get active accounts, check each for tickets, filter.",
            "expected": "Should list active accounts with at least one open ticket"
        },
        {
            "name": "CASE 4: High-Priority Ticket Logging",
            "message": "URGENT! I was charged twice for my subscription! I need a refund immediately! My account ID is 1.",
            "notes": "Support Agent must recognize urgency and log a 'high' priority ticket.",
            "expected": "Should create high priority ticket for billing/refund issue"
        },
        {
            "name": "CASE 5: Multi-Step Record Update and History Check",
            "message": "For customer ID 5: change their email to newaddress@corp.com and then show me their complete ticket history.",
            "notes": "Sequential: Update email (Data Agent) then retrieve history (Data Agent).",
            "expected": "Should update email successfully and display ticket history"
        },
    ]

    summary_results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {test['name']}")
        print(f"Notes: {test['notes']}")
        print(f"Expected: {test['expected']}")
        print("-" * 80)
        
        try:
            await asyncio.sleep(5.0)
            final_result = await test_comms_client.dispatch_message(orchestrator_url, test["message"])
            print(f"\n✓ RESPONSE:\n{final_result}")
            summary_results.append({"case": test["name"], "status": "PASS"})
        except Exception as e:
            print(f"\n✗ EXECUTION ERROR: {e}")
            summary_results.append({"case": test["name"], "status": "FAIL", "error": str(e)})

    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)
    for result in summary_results:
        status_icon = "✓ PASS" if result["status"] == "PASS" else "✗ FAIL"
        print(f"{status_icon} - {result['case']}")
        if "error" in result:
            print(f"    Error Detail: {result['error']}")
    print("="*80 + "\n")