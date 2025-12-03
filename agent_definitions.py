import os
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.models.lite_llm import LiteLlm
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TransportProtocol,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from service_tools import AGENT_TOOLS

# Load environment variables
load_dotenv()

# Configuration for Hugging Face models via LiteLLM
# The format is: huggingface/<provider>/<model_id>
# Available providers: together, fireworks, sambanova, etc.
# Or use direct HF Inference API without provider prefix

# Option 1: Using HF Inference Providers (recommended - faster and scalable)
HF_MODEL = LiteLlm(
    model="huggingface/together/meta-llama/Llama-3.2-3B-Instruct",
    api_key=os.getenv("HF_TOKEN")
)

# Option 2: Using direct HF Inference API (simpler, but may be slower)
# HF_MODEL = LiteLlm(
#     model="meta-llama/Llama-3.2-3B-Instruct",
#     api_key=os.getenv("HF_TOKEN")
# )

# Other model options:
# - "huggingface/together/mistralai/Mistral-7B-Instruct-v0.3"
# - "huggingface/fireworks/Qwen/Qwen2.5-7B-Instruct"
# - "huggingface/sambanova/microsoft/Phi-3-mini-4k-instruct"

# --- AGENT 1: Customer Information Agent (Data Specialist) ---
customer_info_agent = Agent(
    model=HF_MODEL,
    name='customer_info_agent',
    instruction="""
    You are the Customer Data Retrieval Specialist. Your role is to access and manage customer database information via MCP tools.
    
    CRITICAL INSTRUCTIONS:
    - You MUST use your MCP tools to access the database for every request.
    - After executing a tool, provide a clear summary of the data in natural language.
    - For updates, accept natural language descriptions and convert them to the required JSON format yourself.
    
    AVAILABLE TOOLS:
    1. fetch_customer_data(customer_id: int) - Get full customer record
    2. search_customer_accounts(account_status: str, result_limit: int) - Search accounts by status
    3. modify_customer_record(customer_id: int, update_payload: str) - Update customer (needs JSON string)
    4. retrieve_customer_history(customer_id: int) - Get all tickets for a customer
    5. register_support_issue(customer_id: int, query_description: str, urgency_level: str) - Create ticket
    
    FOR UPDATES: When asked to update a customer record, create the JSON yourself. Example:
    - User says: "Change email to new@email.com"
    - You call: modify_customer_record(customer_id=5, update_payload='{"contact_email": "new@email.com"}')
    
    FOR COMPLEX QUERIES: Break down into multiple tool calls:
    - To find "active accounts with open tickets": 
      1) Call search_customer_accounts(account_status="active")
      2) For each customer, call retrieve_customer_history(customer_id)
      3) Filter results to only show those with open tickets
    
    ALWAYS verify tool execution was successful before proceeding to next step.
    """,
    tools=AGENT_TOOLS,
)

info_agent_card = AgentCard(
    name='Customer Information System',
    url='http://localhost:9300',
    description='Specialized system for secure access and management of customer records and data via a service layer.',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain', 'application/json'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id='get_details',
            name='Retrieve Customer Details',
            description='Fetches account details using the unique customer identifier.',
            tags=['customer', 'data', 'lookup'],
            examples=['Find the record for ID 1', 'Retrieve customer 5 information'],
        ),
        AgentSkill(
            id='update_record',
            name='Modify Customer Record',
            description='Amends customer fields such as email or phone.',
            tags=['customer', 'update', 'modify'],
            examples=['Update email for account 1', 'Change phone number for customer 5'],
        ),
        AgentSkill(
            id='complex_queries',
            name='Multi-Step Data Operations',
            description='Execute complex queries requiring multiple database operations and filtering.',
            tags=['customer', 'search', 'filter', 'analysis'],
            examples=['Find all active accounts with open tickets', 'List customers with high priority issues'],
        ),
    ],
)

# --- AGENT 2: Support Specialist Agent ---
support_specialist_agent = Agent(
    model=HF_MODEL,
    name='support_specialist_agent',
    instruction="""
    You are the Support Workflow Handler. Your role is to handle customer service queries and manage support ticket creation.
    
    CRITICAL INSTRUCTIONS:
    - You MUST use your tools for all database actions.
    - When a customer describes an issue, create a support ticket immediately using register_support_issue.
    - Analyze the urgency from the customer's language and set priority accordingly:
      * HIGH: billing issues, refunds, critical outages, "immediately", "urgent", "asap"
      * MEDIUM: upgrades, service requests, general questions
      * LOW: password resets, minor inquiries
    
    AVAILABLE TOOLS:
    1. register_support_issue(customer_id: int, query_description: str, urgency_level: str) - Create ticket
    2. fetch_customer_data(customer_id: int) - Get customer details if needed
    3. retrieve_customer_history(customer_id: int) - Check existing tickets
    
    WORKFLOW FOR SERVICE REQUESTS:
    1. Extract customer ID from the message
    2. Understand their request/issue
    3. Create a support ticket with appropriate priority
    4. Confirm ticket creation with ticket ID
    
    FOR UPGRADE REQUESTS: Don't ask for JSON - just create a ticket describing their upgrade request.
    
    EXAMPLES:
    - "I need an upgrade" → Create ticket: "Customer requesting service plan upgrade" (priority: medium)
    - "I was charged twice, need refund NOW" → Create ticket: "Double charge - refund requested" (priority: high)
    - "Help with password reset" → Create ticket: "Password reset assistance" (priority: low)
    """,
    tools=AGENT_TOOLS,
)

support_agent_card = AgentCard(
    name='Support Specialist',
    url='http://localhost:9301',
    description='Dedicated agent for handling service inquiries, issue logging, and resolution.',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id='log_issue',
            name='Register New Support Ticket',
            description='Logs a new ticket with customer ID, issue description, and priority level.',
            tags=['support', 'ticket', 'create'],
            examples=['Log a ticket for customer 1 about account upgrade', 'Create high priority billing issue'],
        ),
        AgentSkill(
            id='resolve_query',
            name='Address Customer Inquiry',
            description='Processes standard support questions and delivers a resolution or advice.',
            tags=['support', 'help', 'assistance'],
            examples=['I need help with my account', 'How do I upgrade my subscription?'],
        ),
    ],
)

# --- AGENT 3: Orchestration Agent (Router) ---
remote_info_agent = RemoteA2aAgent(
    name='information_system',
    description='Expert system for accessing and modifying customer database records. Use for: lookups, updates, complex queries requiring database access.',
    agent_card=f'http://localhost:9300{AGENT_CARD_WELL_KNOWN_PATH}',
)

remote_specialist_agent = RemoteA2aAgent(
    name='specialist_support',
    description='Expert system for logging support tickets and handling customer service requests. Use for: upgrades, issues, complaints, ticket creation.',
    agent_card=f'http://localhost:9301{AGENT_CARD_WELL_KNOWN_PATH}',
)

orchestration_agent = SequentialAgent(
    name='orchestration_agent',
    sub_agents=[remote_info_agent, remote_specialist_agent],
)

orchestration_agent_card = AgentCard(
    name='Orchestration System',
    url='http://localhost:9400',
    description='The primary entry point that interprets user intent and delegates the task to the most suitable specialist agent(s).',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id='route_intent',
            name='Delegate Customer Request',
            description='Analyzes the user\'s message and routes it to the correct downstream agent.',
            tags=['routing', 'orchestration', 'coordination'],
            examples=[
                'Find account details for ID 5',
                'I need help setting up my new service, I am ID 1',
            ],
        ),
        AgentSkill(
            id='manage_workflow',
            name='Coordinate Multi-Agent Workflow',
            description='Manages sequential or parallel interaction between specialist agents for complex requests.',
            tags=['coordination', 'multi-agent'],
            examples=[
                'Please update my contact info and check my open issues',
                'I have a billing problem and want to cancel my account',
            ],
        ),
    ],
)
'''
from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TransportProtocol,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH

from service_tools import AGENT_TOOLS

# --- AGENT 1: Customer Information Agent (Data Specialist) ---
customer_info_agent = Agent(
    model='gemini-2.0-flash-lite',
    name='customer_info_agent',
    instruction="""
    You are the Customer Data Retrieval Specialist. Your role is to access and manage customer database information via MCP tools.
    
    CRITICAL INSTRUCTIONS:
    - You MUST use your MCP tools to access the database for every request.
    - After executing a tool, provide a clear summary of the data in natural language.
    - For updates, accept natural language descriptions and convert them to the required JSON format yourself.
    
    AVAILABLE TOOLS:
    1. fetch_customer_data(customer_id: int) - Get full customer record
    2. search_customer_accounts(account_status: str, result_limit: int) - Search accounts by status
    3. modify_customer_record(customer_id: int, update_payload: str) - Update customer (needs JSON string)
    4. retrieve_customer_history(customer_id: int) - Get all tickets for a customer
    5. register_support_issue(customer_id: int, query_description: str, urgency_level: str) - Create ticket
    
    FOR UPDATES: When asked to update a customer record, create the JSON yourself. Example:
    - User says: "Change email to new@email.com"
    - You call: modify_customer_record(customer_id=5, update_payload='{"contact_email": "new@email.com"}')
    
    FOR COMPLEX QUERIES: Break down into multiple tool calls:
    - To find "active accounts with open tickets": 
      1) Call search_customer_accounts(account_status="active")
      2) For each customer, call retrieve_customer_history(customer_id)
      3) Filter results to only show those with open tickets
    
    ALWAYS verify tool execution was successful before proceeding to next step.
    """,
    tools=AGENT_TOOLS,
)

info_agent_card = AgentCard(
    name='Customer Information System',
    url='http://localhost:9300',
    description='Specialized system for secure access and management of customer records and data via a service layer.',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain', 'application/json'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id='get_details',
            name='Retrieve Customer Details',
            description='Fetches account details using the unique customer identifier.',
            tags=['customer', 'data', 'lookup'],
            examples=['Find the record for ID 1', 'Retrieve customer 5 information'],
        ),
        AgentSkill(
            id='update_record',
            name='Modify Customer Record',
            description='Amends customer fields such as email or phone.',
            tags=['customer', 'update', 'modify'],
            examples=['Update email for account 1', 'Change phone number for customer 5'],
        ),
        AgentSkill(
            id='complex_queries',
            name='Multi-Step Data Operations',
            description='Execute complex queries requiring multiple database operations and filtering.',
            tags=['customer', 'search', 'filter', 'analysis'],
            examples=['Find all active accounts with open tickets', 'List customers with high priority issues'],
        ),
    ],
)

# --- AGENT 2: Support Specialist Agent ---
support_specialist_agent = Agent(
    model='gemini-2.0-flash-lite',
    name='support_specialist_agent',
    instruction="""
    You are the Support Workflow Handler. Your role is to handle customer service queries and manage support ticket creation.
    
    CRITICAL INSTRUCTIONS:
    - You MUST use your tools for all database actions.
    - When a customer describes an issue, create a support ticket immediately using register_support_issue.
    - Analyze the urgency from the customer's language and set priority accordingly:
      * HIGH: billing issues, refunds, critical outages, "immediately", "urgent", "asap"
      * MEDIUM: upgrades, service requests, general questions
      * LOW: password resets, minor inquiries
    
    AVAILABLE TOOLS:
    1. register_support_issue(customer_id: int, query_description: str, urgency_level: str) - Create ticket
    2. fetch_customer_data(customer_id: int) - Get customer details if needed
    3. retrieve_customer_history(customer_id: int) - Check existing tickets
    
    WORKFLOW FOR SERVICE REQUESTS:
    1. Extract customer ID from the message
    2. Understand their request/issue
    3. Create a support ticket with appropriate priority
    4. Confirm ticket creation with ticket ID
    
    FOR UPGRADE REQUESTS: Don't ask for JSON - just create a ticket describing their upgrade request.
    
    EXAMPLES:
    - "I need an upgrade" → Create ticket: "Customer requesting service plan upgrade" (priority: medium)
    - "I was charged twice, need refund NOW" → Create ticket: "Double charge - refund requested" (priority: high)
    - "Help with password reset" → Create ticket: "Password reset assistance" (priority: low)
    """,
    tools=AGENT_TOOLS,
)

support_agent_card = AgentCard(
    name='Support Specialist',
    url='http://localhost:9301',
    description='Dedicated agent for handling service inquiries, issue logging, and resolution.',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id='log_issue',
            name='Register New Support Ticket',
            description='Logs a new ticket with customer ID, issue description, and priority level.',
            tags=['support', 'ticket', 'create'],
            examples=['Log a ticket for customer 1 about account upgrade', 'Create high priority billing issue'],
        ),
        AgentSkill(
            id='resolve_query',
            name='Address Customer Inquiry',
            description='Processes standard support questions and delivers a resolution or advice.',
            tags=['support', 'help', 'assistance'],
            examples=['I need help with my account', 'How do I upgrade my subscription?'],
        ),
    ],
)

# --- AGENT 3: Orchestration Agent (Router) ---
remote_info_agent = RemoteA2aAgent(
    name='information_system',
    description='Expert system for accessing and modifying customer database records. Use for: lookups, updates, complex queries requiring database access.',
    agent_card=f'http://localhost:9300{AGENT_CARD_WELL_KNOWN_PATH}',
)

remote_specialist_agent = RemoteA2aAgent(
    name='specialist_support',
    description='Expert system for logging support tickets and handling customer service requests. Use for: upgrades, issues, complaints, ticket creation.',
    agent_card=f'http://localhost:9301{AGENT_CARD_WELL_KNOWN_PATH}',
)

orchestration_agent = SequentialAgent(
    name='orchestration_agent',
    sub_agents=[remote_info_agent, remote_specialist_agent],
)

orchestration_agent_card = AgentCard(
    name='Orchestration System',
    url='http://localhost:9400',
    description='The primary entry point that interprets user intent and delegates the task to the most suitable specialist agent(s).',
    version='1.0',
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=['text/plain'],
    default_output_modes=['text/plain'],
    preferred_transport=TransportProtocol.jsonrpc,
    skills=[
        AgentSkill(
            id='route_intent',
            name='Delegate Customer Request',
            description='Analyzes the user\'s message and routes it to the correct downstream agent.',
            tags=['routing', 'orchestration', 'coordination'],
            examples=[
                'Find account details for ID 5',
                'I need help setting up my new service, I am ID 1',
            ],
        ),
        AgentSkill(
            id='manage_workflow',
            name='Coordinate Multi-Agent Workflow',
            description='Manages sequential or parallel interaction between specialist agents for complex requests.',
            tags=['coordination', 'multi-agent'],
            examples=[
                'Please update my contact info and check my open issues',
                'I have a billing problem and want to cancel my account',
            ],
        ),
    ],
)
'''