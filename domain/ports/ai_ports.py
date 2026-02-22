"""
AI Provider Ports

Architectural Intent:
- Defines port interfaces for AI agent operations
- Enables swappable AI providers (Claude, Gemini, OpenAI, custom)
- Supports structured output schemas for AI-native patterns
"""

from abc import ABC, abstractmethod
from typing import Protocol, Any, Callable
from uuid import UUID
from dataclasses import dataclass

from domain.entities.agent import Agent


@dataclass
class TaskResult:
    task_id: UUID
    status: str
    result: Any | None = None
    error: str | None = None
    tokens_used: int = 0


@dataclass
class CompletionRequest:
    agent_id: UUID
    prompt: str
    system_prompt: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    stop_sequences: list[str] | None = None


@dataclass
class CompletionResponse:
    content: str
    tokens_used: int
    model: str
    finish_reason: str


class AIProviderPort(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...
    async def stream_complete(
        self, request: CompletionRequest, callback: Callable[[str], None]
    ) -> CompletionResponse: ...


class AgentExecutorPort(Protocol):
    async def execute_task(
        self, agent: Agent, task: str, context: dict
    ) -> TaskResult: ...
    async def execute_workflow(
        self, agent: Agent, steps: list[dict], context: dict
    ) -> list[TaskResult]: ...
