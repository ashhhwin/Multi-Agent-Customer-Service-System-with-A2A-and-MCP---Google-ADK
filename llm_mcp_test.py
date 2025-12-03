"""
llm_mcp_test.py: Standalone test script for core LLM + MCP Tool integration.

This script executes all five original integration scenarios against a single agent 
to verify complex tool use, multi-step execution, and output stability.
"""
import sys
import os
import logging
import asyncio 
from dotenv import load_dotenv
from google.genai import types
import json # Used for pretty printing raw tool results

# --- Environment and Database Setup (Unchanged) ---
load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    print("FATAL: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)

try:
    from mcp_server import initialize_database_schema
    # NOTE: The MCP server must be running separately for this script to work!
    initialize_database_schema()
    from service_tools import AGENT_TOOLS, _execute_mcp_operation
except ImportError:
    print("FATAL: Cannot load necessary components (mcp_server or service_tools).")
    sys.exit(1)

# --- LLM Agent Definition ---
try:
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.sessions import InMemorySessionService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
except ImportError:
    print("FATAL: Google ADK libraries not found.")
    sys.exit(1)

# Agent definition is expanded to handle all tasks (data, ticket, update)
test_agent = Agent(
    model="gemini-2.5-flash",
    name="Test_Tool_Agent",
    instruction="""
    You are a testing and workflow agent capable of handling all customer service requests (data retrieval, updating records, creating tickets, and checking history).
    Analyze the request and use the appropriate tool(s) to fulfill the task.
    Return a clear and concise summary of the result.
    """,
    tools=AGENT_TOOLS,
)

# --- Runner Function (ASYNCHRONOUS) ---
async def run_detailed_test(query: str): 
    print(f"\n\n--- RUNNING TEST: {query} ---")

    runner = Runner(
        app_name="TestRunner",
        agent=test_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    
    session = await runner.session_service.create_session(user_id="test_user", app_name="TestRunner")
    session_id = session.id 

    try:
        message_content = types.Content(parts=[types.Part(text=query)])
        events_generator = runner.run(
            user_id="test_user", 
            session_id=session_id, 
            new_message=message_content  
        )
        
        final_text = ""
        
        print("\n--- AGENT EXECUTION TRACE ---")
        
        for i, event in enumerate(events_generator, start=1): 
            
            # 1. Capture and display Tool Calls (Input to MCP)
            if hasattr(event, 'actions') and event.actions:
                if hasattr(event.actions, 'function_call') and event.actions.function_call:
                    call = event.actions.function_call
                    print(f"[{i}.0] 🛠️ TOOL CALL: {call.name}")
                    print(f"      Args: {dict(call.args)}")

            # 2. Capture and display Tool Results (Output from MCP)
            if hasattr(event, 'actions') and event.actions:
                if hasattr(event.actions, 'function_response') and event.actions.function_response:
                    response = event.actions.function_response.response
                    
                    print(f"[{i}.1] 💾 TOOL RESPONSE (RAW):")
                    
                    # Try to parse the string result into JSON for clean printing
                    try:
                        parsed_output = json.loads(response)
                        print(json.dumps(parsed_output, indent=2))
                    except (json.JSONDecodeError, TypeError):
                        print(response)
            
            # 3. Capture the final formatted text from the LLM
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        final_text += part.text

        print("\n--- FINAL CONSOLIDATED RESPONSE ---")
        print(final_text.strip() if final_text else "Error: LLM did not return final text (ADK bug).")
        print("-----------------------------------")

    except Exception as e:
        print(f"\n!!! AGENT RUN FAILED: {type(e).__name__} !!!")
        print(f"Error details: {e}")


# --- Main Execution Wrapper ---
async def main_test_wrapper():
    """Executes all 5 test cases asynchronously."""
    
    test_cases = [
        "Please get the full record for customer ID 1",
        "I am customer ID 2 and need to upgrade my service plan.",
        "Provide a list of all active accounts that currently have open tickets.",
        "I was charged twice, I need a refund immediately! Account ID 1.",
        "Change account ID 5's email to newemail@corp.com and then show me their ticket history.",
    ]
    
    for query in test_cases:
        await run_detailed_test(query)
        await asyncio.sleep(1) # Small pause between tests

if __name__ == "__main__":
    print("--- Starting Single-Agent Diagnostic Tool Chain Test ---")
    print("NOTE: The MCP Server must be running on port 8000 for tool execution to succeed.")
    
    try:
        asyncio.run(main_test_wrapper())
    except Exception as e:
        print(f"\nFATAL CRASH IN ASYNC WRAPPER: {e}")