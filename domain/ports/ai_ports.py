"""
AI Provider Ports

Architectural Intent:
- Defines port interfaces for AI agent operations
- Enables swappable AI providers (Claude, Gemini, OpenAI, custom)
- Supports structured output schemas for AI-native patterns (5.6)
- Context window management with token budgeting (5.7)

MCP Integration:
- AI providers exposed via agent-service MCP server
- Tools: execute_task, complete
- Resources: agent://{agent_id}/history

Parallelization Strategy:
- Multiple agents can execute tasks concurrently via AgentExecutorPort
- Fan-out independent task execution, fan-in results
"""

from abc import ABC, abstractmethod
from typing import Protocol, Any, Callable
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum

from domain.entities.agent import Agent


# --- 5.6: Typed AI Output Schemas ---

class OutputFormat(Enum):
    """Supported structured output formats for AI responses."""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass(frozen=True)
class OutputSchema:
    """Schema definition for structured AI output validation (5.6).

    Prevents anti-pattern #9 (Untyped AI output) by requiring
    explicit schema definitions for AI responses.
    """
    format: OutputFormat = OutputFormat.TEXT
    json_schema: dict | None = None
    required_fields: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""

    def validate(self, content: str) -> bool:
        """Validate content against schema."""
        if self.format == OutputFormat.TEXT:
            return bool(content.strip())
        if self.format == OutputFormat.JSON:
            import json as _json
            try:
                parsed = _json.loads(content)
                if self.required_fields:
                    return all(f in parsed for f in self.required_fields)
                return True
            except _json.JSONDecodeError:
                return False
        return True


# --- 5.7: Context Window Management ---

@dataclass
class ContextBudget:
    """Token budget for context window management (5.7).

    Prevents anti-pattern #10 (Context stuffing) by explicitly
    budgeting tokens across system prompt, history, and user input.
    """
    max_tokens: int = 128000
    system_prompt_budget: int = 2000
    history_budget: int = 80000
    user_input_budget: int = 8000
    output_budget: int = 4096

    @property
    def available_for_history(self) -> int:
        return self.max_tokens - self.system_prompt_budget - self.user_input_budget - self.output_budget

    def trim_history(self, messages: list[dict], tokens_per_message: int = 4) -> list[dict]:
        """Trim conversation history to fit within budget.

        Uses approximate token counting (chars / 4) and removes
        oldest messages first, always keeping the most recent.
        """
        if not messages:
            return messages

        budget = self.available_for_history
        result: list[dict] = []
        total = 0

        for msg in reversed(messages):
            est_tokens = len(msg.get("content", "")) // tokens_per_message
            if total + est_tokens > budget:
                break
            result.insert(0, msg)
            total += est_tokens

        return result


# --- Core Data Types ---

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
    model: str | None = None
    system_prompt: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    stop_sequences: list[str] | None = None
    output_schema: OutputSchema | None = None
    context_budget: ContextBudget | None = None
    conversation_history: list[dict] | None = None


@dataclass
class CompletionResponse:
    content: str
    tokens_used: int
    model: str
    finish_reason: str
    schema_valid: bool = True


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
