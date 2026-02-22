"""
Application DTOs

Architectural Intent:
- Data Transfer Objects for layer communication
- Serialization/deserialization between layers
- Structured schemas for AI-native patterns (following skill2026.md)
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Literal


@dataclass
class CloudProviderDTO:
    id: str
    provider_type: str
    name: str
    status: str
    region: str
    account_id: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, entity) -> "CloudProviderDTO":
        return cls(
            id=str(entity.id),
            provider_type=entity.provider_type.value,
            name=entity.name,
            status=entity.status.value,
            region=entity.region,
            account_id=entity.account_id,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_type": self.provider_type,
            "name": self.name,
            "status": self.status,
            "region": self.region,
            "account_id": self.account_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ResourceDTO:
    id: str
    provider_id: str
    resource_type: str
    name: str
    state: str
    region: str
    arn: str | None
    metadata: dict
    tags: dict
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, entity) -> "ResourceDTO":
        return cls(
            id=str(entity.id),
            provider_id=str(entity.provider_id),
            resource_type=entity.resource_type.value,
            name=entity.name,
            state=entity.state.value,
            region=entity.region,
            arn=entity.arn,
            metadata=entity.metadata,
            tags=entity.tags,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "resource_type": self.resource_type,
            "name": self.name,
            "state": self.state,
            "region": self.region,
            "arn": self.arn,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AgentDTO:
    id: str
    name: str
    description: str
    status: str
    provider: str
    model: str
    max_tokens: int
    temperature: float
    capabilities: list[dict]
    created_at: str
    updated_at: str

    @classmethod
    def from_entity(cls, entity) -> "AgentDTO":
        return cls(
            id=str(entity.id),
            name=entity.name,
            description=entity.description,
            status=entity.status.value,
            provider=entity.config.provider.value,
            model=entity.config.model,
            max_tokens=entity.config.max_tokens,
            temperature=entity.config.temperature,
            capabilities=[
                {"name": c.name, "description": c.description}
                for c in entity.capabilities
            ],
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class CostAnalysisDTO:
    current_month_cost: dict
    cost_breakdown: dict
    monthly_forecast: dict
    recommendations: list[dict]


@dataclass
class TaskExecutionDTO:
    task_id: str
    agent_id: str
    task: str
    status: str
    result: str | None
    error: str | None
    tokens_used: int
    started_at: str
    completed_at: str | None
