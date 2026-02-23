"""
HMAS Agent Hierarchy (PRD 4.1, 4.2)

Architectural Intent:
- Implements Hierarchical Multi-Agent System (HMAS) with L3/L2/L1 levels
- EPA (Executive Planning Agent) at L3 orchestrates L2 specialist agents
- L2 agents: RSA, FIA, GA, MVA, DOA, PMA
- L1 agents: task-specific workers delegated by L2

MCP Integration:
- Exposed via agent-service MCP server
- Tools: create_hmas_agent, delegate_task, get_hierarchy
- Resources: hmas://hierarchy, hmas://{agent_id}/children

Parallelization Strategy:
- L2 agents execute independent tasks concurrently
- L1 agents under different L2 parents run in parallel
- Fan-out from EPA to L2, fan-in results
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional

from domain.exceptions import DomainError


class HMASLevel(Enum):
    """Agent hierarchy level per PRD HMAS specification."""
    L3_EXECUTIVE = "L3"    # Executive Planning Agent
    L2_SPECIALIST = "L2"   # Domain specialist agents
    L1_WORKER = "L1"       # Task-specific workers


class HMASRole(Enum):
    """Predefined agent roles from PRD specification."""
    EPA = "EPA"   # Executive Planning Agent (L3)
    RSA = "RSA"   # Refactoring Strategy Agent (L2)
    FIA = "FIA"   # Financial Insight Agent (L2)
    GA = "GA"     # Governance Agent (L2)
    MVA = "MVA"   # Migration Velocity Agent (L2)
    DOA = "DOA"   # Deployment Orchestration Agent (L2)
    PMA = "PMA"   # Performance Monitoring Agent (L2)
    WORKER = "WORKER"  # Generic L1 worker


ROLE_DESCRIPTIONS = {
    HMASRole.EPA: "Executive Planning Agent: orchestrates all L2 agents, creates migration plans, prioritizes tasks",
    HMASRole.RSA: "Refactoring Strategy Agent: analyzes codebase for modernization opportunities, recommends patterns",
    HMASRole.FIA: "Financial Insight Agent: cost analysis, budget forecasting, ROI calculations",
    HMASRole.GA: "Governance Agent: compliance checks, security policies, audit trail management",
    HMASRole.MVA: "Migration Velocity Agent: tracks migration progress, estimates timelines, identifies bottlenecks",
    HMASRole.DOA: "Deployment Orchestration Agent: CI/CD pipelines, blue-green deployments, rollback strategies",
    HMASRole.PMA: "Performance Monitoring Agent: metrics collection, alerting, SLA compliance, anomaly detection",
    HMASRole.WORKER: "Task Worker: executes specific tasks delegated by L2 agents",
}

ROLE_LEVELS = {
    HMASRole.EPA: HMASLevel.L3_EXECUTIVE,
    HMASRole.RSA: HMASLevel.L2_SPECIALIST,
    HMASRole.FIA: HMASLevel.L2_SPECIALIST,
    HMASRole.GA: HMASLevel.L2_SPECIALIST,
    HMASRole.MVA: HMASLevel.L2_SPECIALIST,
    HMASRole.DOA: HMASLevel.L2_SPECIALIST,
    HMASRole.PMA: HMASLevel.L2_SPECIALIST,
    HMASRole.WORKER: HMASLevel.L1_WORKER,
}


@dataclass(frozen=True)
class AgentCard:
    """A2A Agent Card (PRD 4.3) - Describes agent capabilities for inter-agent communication."""
    agent_id: UUID
    name: str
    role: HMASRole
    level: HMASLevel
    description: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    mcp_tools: tuple[str, ...] = field(default_factory=tuple)
    supported_protocols: tuple[str, ...] = ("a2a", "mcp")
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "agent_id": str(self.agent_id),
            "name": self.name,
            "role": self.role.value,
            "level": self.level.value,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "mcp_tools": list(self.mcp_tools),
            "supported_protocols": list(self.supported_protocols),
            "version": self.version,
        }


@dataclass(frozen=True)
class HMASAgent:
    """
    Hierarchical Multi-Agent System agent entity.
    Immutable per Rule 3.
    """
    id: UUID
    name: str
    role: HMASRole
    level: HMASLevel
    description: str
    parent_id: Optional[UUID] = None
    children_ids: tuple[UUID, ...] = field(default_factory=tuple)
    status: str = "active"
    model: str = "gemini-2.0-flash"
    system_prompt: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple = field(default_factory=tuple)

    def __post_init__(self):
        expected_level = ROLE_LEVELS.get(self.role)
        if expected_level and self.level != expected_level:
            raise DomainError(
                f"Role {self.role.value} must be level {expected_level.value}, got {self.level.value}"
            )

    def add_child(self, child_id: UUID) -> "HMASAgent":
        if self.level == HMASLevel.L1_WORKER:
            raise DomainError("L1 workers cannot have children")
        if child_id in self.children_ids:
            raise DomainError(f"Child {child_id} already exists")
        return replace(
            self,
            children_ids=self.children_ids + (child_id,),
            domain_events=self.domain_events + (
                AgentChildAddedEvent(self.id, child_id),
            ),
        )

    def remove_child(self, child_id: UUID) -> "HMASAgent":
        if child_id not in self.children_ids:
            raise DomainError(f"Child {child_id} not found")
        return replace(
            self,
            children_ids=tuple(c for c in self.children_ids if c != child_id),
        )

    def get_agent_card(self) -> AgentCard:
        return AgentCard(
            agent_id=self.id,
            name=self.name,
            role=self.role,
            level=self.level,
            description=self.description or ROLE_DESCRIPTIONS.get(self.role, ""),
        )

    def delegate_task(self, task: str, target_child_id: UUID) -> "HMASAgent":
        if target_child_id not in self.children_ids:
            raise DomainError(f"Cannot delegate to non-child agent {target_child_id}")
        return replace(
            self,
            domain_events=self.domain_events + (
                TaskDelegatedEvent(
                    from_agent_id=self.id,
                    to_agent_id=target_child_id,
                    task=task,
                ),
            ),
        )


@dataclass(frozen=True)
class AgentChildAddedEvent:
    parent_id: UUID
    child_id: UUID
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class TaskDelegatedEvent:
    from_agent_id: UUID
    to_agent_id: UUID
    task: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def create_default_hierarchy() -> list[HMASAgent]:
    """Create the default HMAS hierarchy per PRD specification."""
    epa_id = uuid4()

    agents = [
        HMASAgent(
            id=epa_id,
            name="Executive Planning Agent",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description=ROLE_DESCRIPTIONS[HMASRole.EPA],
            system_prompt="You are the EPA, the top-level orchestrator. Delegate tasks to L2 specialist agents.",
        ),
    ]

    l2_roles = [HMASRole.RSA, HMASRole.FIA, HMASRole.GA, HMASRole.MVA, HMASRole.DOA, HMASRole.PMA]
    l2_ids = []

    for role in l2_roles:
        agent_id = uuid4()
        l2_ids.append(agent_id)
        agents.append(HMASAgent(
            id=agent_id,
            name=f"{role.value} Agent",
            role=role,
            level=HMASLevel.L2_SPECIALIST,
            description=ROLE_DESCRIPTIONS[role],
            parent_id=epa_id,
            system_prompt=f"You are the {role.value} agent. {ROLE_DESCRIPTIONS[role]}",
        ))

    # Update EPA with children
    agents[0] = replace(agents[0], children_ids=tuple(l2_ids))

    return agents


__all__ = [
    "HMASLevel", "HMASRole", "HMASAgent", "AgentCard",
    "ROLE_DESCRIPTIONS", "ROLE_LEVELS",
    "AgentChildAddedEvent", "TaskDelegatedEvent",
    "create_default_hierarchy",
]
