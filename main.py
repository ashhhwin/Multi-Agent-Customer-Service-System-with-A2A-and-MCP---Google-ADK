"""
main.py: Multi-Agent Customer Service System Entry Point

Initializes the system, starts all A2A and MCP servers, and executes the 
integration test suite. Incorporates all final fixes for robust execution.
"""
import warnings
import asyncio
import time
import logging
import os
import sys
from dotenv import load_dotenv 

# ----------------------------------------------------------------------
# 0. INITIAL SETUP & ENVIRONMENT CHECK
# ----------------------------------------------------------------------

# Suppress UserWarnings (like the [EXPERIMENTAL] ones)
warnings.filterwarnings("ignore", category=UserWarning)

# Load Environment Variables (API Key, etc.) from .env file
load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    print("FATAL: GEMINI_API_KEY environment variable not set. Cannot run LLM agents.")
    sys.exit(1)

# --- VERBOSE LOGGING SETTINGS (Final) ---
# Set the root logger level to INFO to capture all internal ADK and Uvicorn traffic.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)
# Suppress noisy access logs while keeping ADK logs visible
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ----------------------------------------------------------------------
# 1. IMPORT MODULES
# ----------------------------------------------------------------------

# FIX: Using the file name confirmed on disk: a2a_patch
import a2a_patch 

# These imports trigger module-level code (DB init, Tool definition, Agent creation)
import database_utility 
import service_tools
import agent_definitions

# Server deployment and client logic
from server_launcher import start_server_daemon
from client_runner import execute_test_suite

# ----------------------------------------------------------------------
# 2. MAIN EXECUTION BLOCK
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("\n--- Multi-Agent System: Initialization & Test Launch ---")
    
    # Start the A2A servers and MCP server in a background daemon thread
    server_process = start_server_daemon()
    
    print("Waiting for background services to stabilize...")
    time.sleep(5)
    
    print("\n--- Running Integration Test Scenarios ---\n")
    
    # Run the test suite on the main thread
    try:
        # Executes the test client, which hits the Orchestration Agent (Router)
        asyncio.run(execute_test_suite())
    except Exception as e:
        print(f"\nFATAL ERROR DURING TEST EXECUTION: {e}")
    
    print("\n--- All tests completed. Services still running. ---")
    
    # Keep the main thread alive so the daemon thread can continue to serve requests
    try:
        while server_process.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Shutting down.")
    
    print("Application terminated.")