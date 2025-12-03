# Multi-Agent Customer Service System - A2A ADK MCP Implementation

## Overview
This project implements a multi-agent customer service system using Google's Agent Development Kit (ADK) with Agent-to-Agent (A2A) communication protocol and Model Context Protocol (MCP) for database access.

## System Architecture

### Components
1. **MCP Server** (Port 8000)
   - Provides HTTP API layer over SQLite database
   - Handles CRUD operations for customer accounts and support tickets

2. **Customer Information Agent** (Port 9300)
   - Specializes in data retrieval and customer record management
   - Performs lookups, updates, and complex queries

3. **Support Specialist Agent** (Port 9301)
   - Handles customer service inquiries
   - Creates and manages support tickets with priority levels

4. **Orchestration Agent** (Port 9400)
   - Main entry point for user requests
   - Routes queries to appropriate specialist agents
   - Coordinates multi-agent workflows

## File Structure

```
project/
├── a2a_patch.py              # Compatibility patch for A2A client
├── agent_definitions.py      # Agent configurations and capabilities
├── client_runner.py          # Test client and integration test suite
├── database_utility.py       # SQLite connection utilities
├── mcp_server.py            # MCP HTTP server implementation
├── server_launcher.py       # Multi-server orchestration
├── service_tools.py         # MCP tool wrappers for agents
├── main.py                  # Main entry point
├── .env                     # Environment variables (GEMINI_API_KEY)
└── service_db.sqlite        # SQLite database (auto-created)
```

## Prerequisites

### Required Python Packages
```bash
pip install google-adk
pip install a2a
pip install httpx
pip install uvicorn
pip install starlette
pip install python-dotenv
pip install nest-asyncio
pip install pandas  # Optional, for database inspection
```

### Environment Variables
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_gemini_api_key_here
```


## Installation

1. Clone or download all project files to a directory
2. Install required packages (see Prerequisites)
3. Create `.env` file with your GEMINI_API_KEY
4. Ensure all Python files are in the same directory

## Running the System

### Option 1: Command Line
```bash
python main.py
```

This will:
- Initialize the SQLite database with seed data
- Start all four servers (MCP + 3 A2A agents)
- Run the integration test suite automatically
- Keep servers running until interrupted (Ctrl+C)

### Option 2: Jupyter Notebook
Run cells sequentially in the provided notebook for step-by-step execution and better output visualization.

## Test Scenarios

The system includes 5 integration test cases:

1. **Simple Data Retrieval**
   - Fetches complete customer record by ID
   - Tests basic agent routing and tool usage

2. **Coordinated Service Request**
   - Customer requests service upgrade
   - Tests multi-agent coordination and ticket creation

3. **Complex Filtering Query**
   - Lists active accounts with open tickets
   - Tests multi-step queries requiring multiple tool calls

4. **High-Priority Ticket Logging**
   - Urgent billing issue with refund request
   - Tests priority detection and high-urgency ticket creation

5. **Multi-Step Record Update**
   - Updates customer email and retrieves ticket history
   - Tests sequential operations and error handling

## Database Schema

### customer_accounts
- identifier (PRIMARY KEY)
- full_name
- contact_email
- contact_phone
- account_status
- creation_timestamp
- last_modified_timestamp

### support_tickets
- ticket_id (PRIMARY KEY)
- account_id (FOREIGN KEY)
- description
- status
- priority_level (low/medium/high)
- submission_timestamp

## API Endpoints

### MCP Server (http://127.0.0.1:8000)
- GET /tools - List available operations
- POST /call - Execute database operation

### Agent Servers
- GET /.well-known/agent-card.json - Agent capability card
- POST / - Send message to agent (A2A protocol)

## Available MCP Tools

1. **fetch_customer_data(customer_id: int)**
   - Retrieve customer account by ID

2. **search_customer_accounts(account_status: str, result_limit: int)**
   - Search accounts by status (active/disabled)

3. **modify_customer_record(customer_id: int, update_payload: str)**
   - Update customer fields (requires JSON string)

4. **register_support_issue(customer_id: int, query_description: str, urgency_level: str)**
   - Create new support ticket

5. **retrieve_customer_history(customer_id: int)**
   - Get all tickets for a customer
