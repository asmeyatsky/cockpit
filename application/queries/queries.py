"""
Query Handlers (Read Operations - CQRS)

Architectural Intent:
- Separate read path from write path (CQRS pattern)
- Query handlers are lightweight, return DTOs
- Read-optimized, potentially from different store
"""

from uuid import UUID
from typing import Optional

from domain.ports.repository_ports import (
    CloudProviderRepositoryPort,
    ResourceRepositoryPort,
    AgentRepositoryPort,
)
from application.dtos.dtos import CloudProviderDTO, ResourceDTO, AgentDTO


class GetCloudProviderQuery:
    def __init__(self, provider_repo: CloudProviderRepositoryPort):
        self._repo = provider_repo

    async def execute(self, provider_id: str) -> Optional[CloudProviderDTO]:
        provider = await self._repo.get_by_id(UUID(provider_id))
        if provider:
            return CloudProviderDTO.from_entity(provider)
        return None


class ListCloudProvidersQuery:
    def __init__(self, provider_repo: CloudProviderRepositoryPort):
        self._repo = provider_repo

    async def execute(self) -> list[dict]:
        providers = await self._repo.get_all()
        return [CloudProviderDTO.from_entity(p).to_dict() for p in providers]


class GetResourceQuery:
    def __init__(self, resource_repo: ResourceRepositoryPort):
        self._repo = resource_repo

    async def execute(self, resource_id: str) -> Optional[ResourceDTO]:
        resource = await self._repo.get_by_id(UUID(resource_id))
        if resource:
            return ResourceDTO.from_entity(resource)
        return None


class ListResourcesQuery:
    def __init__(self, resource_repo: ResourceRepositoryPort):
        self._repo = resource_repo

    async def execute(
        self,
        provider_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[dict]:
        from domain.entities.resource import ResourceState

        if provider_id:
            resources = await self._repo.get_by_provider(UUID(provider_id))
        else:
            resources = await self._repo.get_all()

        if resource_type:
            from domain.entities.resource import ResourceType

            resources = [
                r for r in resources if r.resource_type == ResourceType(resource_type)
            ]

        if state:
            resources = [r for r in resources if r.state == ResourceState(state)]

        return [ResourceDTO.from_entity(r).to_dict() for r in resources]


class GetAgentQuery:
    def __init__(self, agent_repo: AgentRepositoryPort):
        self._repo = agent_repo

    async def execute(self, agent_id: str) -> Optional[AgentDTO]:
        agent = await self._repo.get_by_id(UUID(agent_id))
        if agent:
            return AgentDTO.from_entity(agent)
        return None


class ListAgentsQuery:
    def __init__(self, agent_repo: AgentRepositoryPort):
        self._repo = agent_repo

    async def execute(self) -> list[dict]:
        agents = await self._repo.get_all()
        return [AgentDTO.from_entity(a).to_dict() for a in agents]
