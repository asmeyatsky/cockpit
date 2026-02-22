"""
AI Agent Domain Entity

Architectural Intent:
- Represents an AI agent configuration in the system
- Agent entity manages provider configuration and capability definitions
- Supports Claude, Gemini, OpenAI, and custom providers

MCP Integration:
- Exposed via agent-service MCP server
- Tools: create_agent, update_agent, delete_agent, execute_task
- Resources: agent://{agent_id}, agent://list
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4


class AIProvider(Enum):
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"
    CUSTOM = "custom"


class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass(frozen=True)
class AgentCapability:
    name: str
    description: str
    mcp_servers: tuple[str, ...]


@dataclass(frozen=True)
class AgentConfig:
    provider: AIProvider
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str = ""


@dataclass(frozen=True)
class Agent:
    id: UUID
    name: str
    description: str
    status: AgentStatus
    config: AgentConfig
    capabilities: tuple[AgentCapability, ...]
    mcp_tools: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple = field(default_factory=tuple)

    def activate(self) -> "Agent":
        if self.status == AgentStatus.ACTIVE:
            raise DomainError("Agent already active")
        return replace(
            self,
            status=AgentStatus.ACTIVE,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (AgentActivatedEvent(self.id, self.name),),
        )

    def deactivate(self) -> "Agent":
        if self.status == AgentStatus.INACTIVE:
            raise DomainError("Agent already inactive")
        return replace(
            self,
            status=AgentStatus.INACTIVE,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (AgentDeactivatedEvent(self.id, self.name),),
        )

    def set_error(self, error: str) -> "Agent":
        return replace(
            self,
            status=AgentStatus.ERROR,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (AgentErrorEvent(self.id, self.name, error),),
        )

    def add_capability(self, capability: AgentCapability) -> "Agent":
        return replace(
            self,
            capabilities=self.capabilities + (capability,),
            updated_at=datetime.now(UTC),
        )


@dataclass(frozen=True)
class AgentActivatedEvent:
    agent_id: UUID
    agent_name: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AgentDeactivatedEvent:
    agent_id: UUID
    agent_name: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class AgentErrorEvent:
    agent_id: UUID
    agent_name: str
    error_message: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DomainError(Exception):
    pass
