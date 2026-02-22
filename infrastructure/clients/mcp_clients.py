"""
MCP Client Adapters

Architectural Intent:
- Consumes external MCP servers as infrastructure adapters
- Wraps MCP client calls behind domain ports
- Following Pattern 2: MCP Client as Infrastructure Adapter
"""

from typing import Protocol, Any, Callable
from uuid import UUID
from dataclasses import dataclass

from domain.ports.ai_ports import (
    AIProviderPort,
    AgentExecutorPort,
    CompletionRequest,
    CompletionResponse,
    TaskResult,
)
from domain.entities.agent import Agent


class MCPClientSession(Protocol):
    async def call_tool(self, tool_name: str, arguments: dict) -> Any: ...
    async def read_resource(self, uri: str) -> Any: ...


class MCPAgentAdapter(AIProviderPort):
    """Adapter that calls an AI provider via MCP."""

    def __init__(self, mcp_session: MCPClientSession):
        self.session = mcp_session

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        result = await self.session.call_tool(
            "complete",
            arguments={
                "prompt": request.prompt,
                "system_prompt": request.system_prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
        )

        return CompletionResponse(
            content=result.get("content", ""),
            tokens_used=result.get("tokens_used", 0),
            model=result.get("model", "unknown"),
            finish_reason=result.get("finish_reason", "stop"),
        )

    async def stream_complete(
        self,
        request: CompletionRequest,
        callback: Callable[[str], None],
    ) -> CompletionResponse:
        result = await self.session.call_tool(
            "stream_complete",
            arguments={
                "prompt": request.prompt,
                "system_prompt": request.system_prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            },
        )

        for chunk in result.get("chunks", []):
            callback(chunk)

        return CompletionResponse(
            content=result.get("content", ""),
            tokens_used=result.get("tokens_used", 0),
            model=result.get("model", "unknown"),
            finish_reason=result.get("finish_reason", "stop"),
        )


class MCPAgentExecutorAdapter(AgentExecutorPort):
    """Adapter that executes agent tasks via MCP."""

    def __init__(self, mcp_session: MCPClientSession):
        self.session = mcp_session

    async def execute_task(self, agent: Agent, task: str, context: dict) -> TaskResult:
        result = await self.session.call_tool(
            "execute_task",
            arguments={
                "agent_id": str(agent.id),
                "task": task,
                "context": context,
            },
        )

        return TaskResult(
            task_id=UUID(result.get("task_id", "00000000-0000-0000-0000-000000000000")),
            status=result.get("status", "completed"),
            result=result.get("result"),
            error=result.get("error"),
            tokens_used=result.get("tokens_used", 0),
        )

    async def execute_workflow(
        self, agent: Agent, steps: list[dict], context: dict
    ) -> list[TaskResult]:
        results = await self.session.call_tool(
            "execute_workflow",
            arguments={
                "agent_id": str(agent.id),
                "steps": steps,
                "context": context,
            },
        )

        return [
            TaskResult(
                task_id=UUID(r.get("task_id", "00000000-0000-0000-0000-000000000000")),
                status=r.get("status", "completed"),
                result=r.get("result"),
                error=r.get("error"),
                tokens_used=r.get("tokens_used", 0),
            )
            for r in results
        ]
