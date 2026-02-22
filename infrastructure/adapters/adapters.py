"""
Infrastructure Adapters

Architectural Intent:
- Concrete implementations of domain ports
- Adapters live in infrastructure layer
- Following Rule 2: Interface-First Development
"""

import asyncio
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from domain.entities.cloud_provider import CloudProvider, ProviderStatus
from domain.entities.resource import Resource, ResourceState
from domain.ports.repository_ports import (
    CloudProviderRepositoryPort,
    ResourceRepositoryPort,
    AgentRepositoryPort,
)
from domain.ports.infrastructure_ports import (
    CloudProviderPort,
    ResourcePort,
    CostPort,
    ObservabilityPort,
    IaCPort,
)
from domain.value_objects.money import Money


class InMemoryCloudProviderRepository:
    def __init__(self):
        self._providers: dict[UUID, CloudProvider] = {}

    async def save(self, provider: CloudProvider) -> CloudProvider:
        self._providers[provider.id] = provider
        return provider

    async def get_by_id(self, provider_id: UUID) -> CloudProvider | None:
        return self._providers.get(provider_id)

    async def get_by_type(self, provider_type) -> list[CloudProvider]:
        return [p for p in self._providers.values() if p.provider_type == provider_type]

    async def get_all(self) -> list[CloudProvider]:
        return list(self._providers.values())

    async def delete(self, provider_id: UUID) -> None:
        self._providers.pop(provider_id, None)


class InMemoryResourceRepository:
    def __init__(self):
        self._resources: dict[UUID, Resource] = {}

    async def save(self, resource: Resource) -> Resource:
        self._resources[resource.id] = resource
        return resource

    async def get_by_id(self, resource_id: UUID) -> Resource | None:
        return self._resources.get(resource_id)

    async def get_by_provider(self, provider_id: UUID) -> list[Resource]:
        return [r for r in self._resources.values() if r.provider_id == provider_id]

    async def get_by_type(self, resource_type) -> list[Resource]:
        return [r for r in self._resources.values() if r.resource_type == resource_type]

    async def get_by_state(self, state: ResourceState) -> list[Resource]:
        return [r for r in self._resources.values() if r.state == state]

    async def get_all(self) -> list[Resource]:
        return list(self._resources.values())

    async def delete(self, resource_id: UUID) -> None:
        self._resources.pop(resource_id, None)


class InMemoryAgentRepository:
    def __init__(self):
        self._agents: dict[UUID, object] = {}

    async def save(self, agent) -> object:
        self._agents[agent.id] = agent
        return agent

    async def get_by_id(self, agent_id: UUID) -> object | None:
        return self._agents.get(agent_id)

    async def get_by_status(self, status) -> list[object]:
        return [a for a in self._agents.values() if a.status == status]

    async def get_all(self) -> list[object]:
        return list(self._agents.values())

    async def delete(self, agent_id: UUID) -> None:
        self._agents.pop(agent_id, None)


class MockCloudProviderAdapter:
    """Mock adapter for cloud provider operations."""

    async def connect(self, provider: CloudProvider) -> bool:
        await asyncio.sleep(0.1)
        return True

    async def disconnect(self, provider: CloudProvider) -> bool:
        await asyncio.sleep(0.1)
        return True

    async def get_status(self, provider: CloudProvider) -> str:
        return "connected"


class MockResourceAdapter:
    """Mock adapter for resource operations."""

    async def create(self, provider: CloudProvider, config: dict) -> Resource:
        from uuid import uuid4

        return Resource(
            id=uuid4(),
            provider_id=provider.id,
            resource_type=config.get("resource_type", "compute_instance"),
            name=config.get("name", "new-resource"),
            state=ResourceState.RUNNING,
            region=provider.region,
        )

    async def start(self, resource: Resource) -> bool:
        await asyncio.sleep(0.1)
        return True

    async def stop(self, resource: Resource) -> bool:
        await asyncio.sleep(0.1)
        return True

    async def terminate(self, resource: Resource) -> bool:
        await asyncio.sleep(0.1)
        return True

    async def get_status(self, resource: Resource) -> str:
        return resource.state.value

    async def update_tags(self, resource: Resource, tags: dict) -> bool:
        await asyncio.sleep(0.1)
        return True


class MockCostAdapter:
    """Mock adapter for cost operations."""

    async def get_current_cost(
        self, provider_id: UUID, start_date: datetime, end_date: datetime
    ) -> Money:
        return Money(1234.56, "USD")

    async def get_cost_breakdown(
        self, provider_id: UUID, start_date: datetime, end_date: datetime
    ) -> dict:
        return {
            "by_service": {
                "compute": Money(500.0, "USD"),
                "storage": Money(200.0, "USD"),
                "network": Money(100.0, "USD"),
            },
            "by_region": {
                "us-east-1": Money(800.0, "USD"),
            },
        }

    async def get_forecast(self, provider_id: UUID, days: int) -> Money:
        return Money(1500.0, "USD")


class MockObservabilityAdapter:
    """Mock adapter for observability operations."""

    async def get_metrics(
        self, provider_id: UUID, metric_name: str, start: datetime, end: datetime
    ) -> list[dict]:
        return [
            {"timestamp": (start + timedelta(hours=i)).isoformat(), "value": 100 + i}
            for i in range(24)
        ]

    async def get_logs(
        self, provider_id: UUID, resource_id: UUID, start: datetime, end: datetime
    ) -> list[str]:
        return [f"Log entry {i}" for i in range(10)]

    async def get_traces(self, provider_id: UUID, trace_id: str) -> dict:
        return {
            "trace_id": trace_id,
            "spans": [],
        }
