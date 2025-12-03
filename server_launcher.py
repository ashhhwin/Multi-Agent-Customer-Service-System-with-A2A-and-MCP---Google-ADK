import asyncio
import threading
import uvicorn
import nest_asyncio
import logging
import time

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from google.adk.a2a.executor.a2a_agent_executor import (
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
)
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from a2a.types import AgentCard

from agent_definitions import (
    customer_info_agent,
    support_specialist_agent,
    orchestration_agent,
    info_agent_card,
    support_agent_card,
    orchestration_agent_card,
)

from mcp_server import run_mcp_server_async

nest_asyncio.apply()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
)
logging.getLogger("uvicorn.server").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

def create_adk_server_application(agent: object, metadata_card: AgentCard) -> A2AStarletteApplication:
    execution_runner = Runner(
        app_name=agent.name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    executor_config = A2aAgentExecutorConfig()
    agent_execution_engine = A2aAgentExecutor(runner=execution_runner, config=executor_config)

    request_flow_handler = DefaultRequestHandler(
        agent_executor=agent_execution_engine,
        task_store=InMemoryTaskStore(),
    )

    return A2AStarletteApplication(
        agent_card=metadata_card, http_handler=request_flow_handler
    )

async def launch_single_agent_server(agent: object, metadata_card: AgentCard, port: int):
    server_app = create_adk_server_application(agent, metadata_card)

    uvicorn_config = uvicorn.Config(
        server_app.build(),
        host='127.0.0.1',
        port=port,
        log_level='info',
        loop='none', 
    )

    server_instance = uvicorn.Server(uvicorn_config)
    print(f"[*] {agent.name.title().replace('_', ' ')} starting on http://127.0.0.1:{port}")
    await server_instance.serve()

async def launch_all_service_servers():
    print("\n" + "="*60)
    print("Initiating All Microservices...")
    print("="*60)
    
    server_launch_tasks = [
        asyncio.create_task(run_mcp_server_async()), 
        
        asyncio.create_task(launch_single_agent_server(customer_info_agent, info_agent_card, 9300)),
        asyncio.create_task(launch_single_agent_server(support_specialist_agent, support_agent_card, 9301)),
        asyncio.create_task(launch_single_agent_server(orchestration_agent, orchestration_agent_card, 9400)),
    ]
    
    await asyncio.sleep(4)
    
    print("\n[READY] All service servers deployed!")
    print(f"    - Orchestration Entry Point: http://127.0.0.1:9400")
    print("="*60 + "\n")
    
    await asyncio.gather(*server_launch_tasks)

def run_servers_in_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(launch_all_service_servers())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nServer background processes shutting down.")
    finally:
        pending_tasks = asyncio.all_tasks(loop)
        for task in pending_tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
        loop.close()

def start_server_daemon():
    server_thread = threading.Thread(target=run_servers_in_background, daemon=True)
    server_thread.start()
    return server_thread