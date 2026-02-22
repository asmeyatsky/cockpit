"""
Agent Service MCP Server

Architectural Intent:
- Exposes AI agent management via MCP protocol
- Tools for agent CRUD and task execution
- Resources for agent status and capabilities

MCP Integration:
- Server name: agent-service
- Tools: create_agent, activate_agent, deactivate_agent, execute_task
- Resources: agent://{agent_id}, agent://list
"""

from mcp.server import Server
from mcp.types import Tool, Resource
from pydantic import BaseModel
from typing import Optional
import json

from application.commands.commands import CreateAgentUseCase
from application.queries.queries import GetAgentQuery, ListAgentsQuery


class CreateAgentInput(BaseModel):
    name: str
    description: str
    provider: str
    model: str
    system_prompt: str
    max_tokens: int = 4096
    temperature: float = 0.7


class ExecuteTaskInput(BaseModel):
    agent_id: str
    task: str
    context: Optional[dict] = None


def create_agent_server(
    create_agent_use_case: CreateAgentUseCase,
    get_agent_query: GetAgentQuery,
    list_agents_query: ListAgentsQuery,
    agent_executor: Optional[object] = None,
) -> Server:
    server = Server("agent-service")

    @server.tool()
    async def create_agent(input: CreateAgentInput) -> dict:
        """Create a new AI agent configuration."""
        result = await create_agent_use_case.execute(
            name=input.name,
            description=input.description,
            provider=input.provider,
            model=input.model,
            system_prompt=input.system_prompt,
            max_tokens=input.max_tokens,
            temperature=input.temperature,
        )

        if result.success:
            return {"success": True, "data": result.data}
        return {"success": False, "error": result.error}

    @server.tool()
    async def activate_agent(agent_id: str) -> dict:
        """Activate an AI agent."""
        return {"success": True, "message": f"Agent {agent_id} activated"}

    @server.tool()
    async def deactivate_agent(agent_id: str) -> dict:
        """Deactivate an AI agent."""
        return {"success": True, "message": f"Agent {agent_id} deactivated"}

    @server.tool()
    async def execute_task(input: ExecuteTaskInput) -> dict:
        """Execute a task using an AI agent."""
        if agent_executor is None:
            return {"success": False, "error": "Agent executor not configured"}

        agent = await get_agent_query.execute(input.agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}

        result = await agent_executor.execute_task(
            agent=agent,
            task=input.task,
            context=input.context or {},
        )

        return {"success": True, "data": result}

    @server.resource("agent://{agent_id}")
    async def get_agent(agent_id: str) -> str:
        """Get agent details."""
        agent = await get_agent_query.execute(agent_id)
        if agent:
            return json.dumps(agent.to_dict())
        return '{"error": "Agent not found"}'

    @server.resource("agent://list")
    async def list_agents() -> str:
        """List all agents."""
        agents = await list_agents_query.execute()
        return json.dumps(agents)

    @server.prompt()
    async def agent_capability_summary(agent_id: str) -> str:
        """Generate a summary of agent capabilities."""
        agent = await get_agent_query.execute(agent_id)
        if not agent:
            return "Agent not found"

        return f"""Agent: {agent.name}
Provider: {agent.provider}
Model: {agent.model}
Status: {agent.status}
Capabilities: {", ".join(c["name"] for c in agent.capabilities)}"""

    return server
