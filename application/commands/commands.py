"""
Application Use Cases

Architectural Intent:
- Orchestrates domain objects via ports
- One use case per class (single responsibility)
- Uses DAG orchestration for multi-step workflows
- Parallelizes independent steps by default
"""

from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, UTC
from typing import Optional

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.entities.agent import (
    Agent,
    AgentCapability,
    AgentConfig,
    AIProvider,
    AgentStatus,
)
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
)
from domain.ports.event_bus_port import EventBusPort
from domain.services.domain_services import ProviderDomainService, ResourceDomainService
from application.dtos.dtos import (
    CloudProviderDTO,
    ResourceDTO,
    AgentDTO,
    CostAnalysisDTO,
)


@dataclass
class UseCaseResult:
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class CreateCloudProviderUseCase:
    def __init__(
        self,
        provider_repo: CloudProviderRepositoryPort,
        event_bus: EventBusPort,
    ):
        self._repo = provider_repo
        self._event_bus = event_bus

    async def execute(
        self,
        provider_type: str,
        name: str,
        region: str,
        account_id: Optional[str] = None,
    ) -> UseCaseResult:
        try:
            provider = CloudProvider(
                id=uuid4(),
                provider_type=CloudProviderType(provider_type),
                name=name,
                status=ProviderStatus.DISCONNECTED,
                region=region,
                account_id=account_id,
            )

            saved_provider = await self._repo.save(provider)

            if saved_provider.domain_events:
                await self._event_bus.publish(list(saved_provider.domain_events))

            return UseCaseResult(
                success=True,
                data=CloudProviderDTO.from_entity(saved_provider).to_dict(),
            )
        except Exception as e:
            return UseCaseResult(success=False, error=str(e))


class ConnectProviderUseCase:
    def __init__(
        self,
        provider_repo: CloudProviderRepositoryPort,
        cloud_provider_port: CloudProviderPort,
        event_bus: EventBusPort,
    ):
        self._repo = provider_repo
        self._cloud_port = cloud_provider_port
        self._event_bus = event_bus

    async def execute(self, provider_id: str) -> UseCaseResult:
        try:
            provider_uuid = UUID(provider_id)
            provider = await self._repo.get_by_id(provider_uuid)

            if not provider:
                return UseCaseResult(success=False, error="Provider not found")

            connected = await self._cloud_port.connect(provider)

            if connected:
                updated_provider = provider.connect()
                await self._repo.save(updated_provider)

                if updated_provider.domain_events:
                    await self._event_bus.publish(list(updated_provider.domain_events))

                return UseCaseResult(
                    success=True,
                    data=CloudProviderDTO.from_entity(updated_provider).to_dict(),
                )
            else:
                return UseCaseResult(
                    success=False, error="Failed to connect to provider"
                )

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))


class CreateResourceUseCase:
    def __init__(
        self,
        resource_repo: ResourceRepositoryPort,
        provider_repo: CloudProviderRepositoryPort,
        resource_port: ResourcePort,
        event_bus: EventBusPort,
    ):
        self._resource_repo = resource_repo
        self._provider_repo = provider_repo
        self._resource_port = resource_port
        self._event_bus = event_bus

    async def execute(
        self,
        provider_id: str,
        resource_type: str,
        name: str,
        region: str,
        config: dict,
        tags: Optional[dict] = None,
    ) -> UseCaseResult:
        try:
            provider_uuid = UUID(provider_id)
            provider = await self._provider_repo.get_by_id(provider_uuid)

            if not provider:
                return UseCaseResult(success=False, error="Provider not found")

            resource = Resource(
                id=uuid4(),
                provider_id=provider_uuid,
                resource_type=ResourceType(resource_type),
                name=name,
                state=ResourceState.PENDING,
                region=region,
                tags=tags or {},
            )

            created_resource = await self._resource_port.create(provider, config)
            saved_resource = await self._resource_repo.save(created_resource)

            if saved_resource.domain_events:
                await self._event_bus.publish(list(saved_resource.domain_events))

            return UseCaseResult(
                success=True,
                data=ResourceDTO.from_entity(saved_resource).to_dict(),
            )

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))


class ManageResourceUseCase:
    def __init__(
        self,
        resource_repo: ResourceRepositoryPort,
        resource_port: ResourcePort,
        event_bus: EventBusPort,
    ):
        self._repo = resource_repo
        self._resource_port = resource_port
        self._event_bus = event_bus

    async def start(self, resource_id: str) -> UseCaseResult:
        try:
            resource_uuid = UUID(resource_id)
            resource = await self._repo.get_by_id(resource_uuid)

            if not resource:
                return UseCaseResult(success=False, error="Resource not found")

            success = await self._resource_port.start(resource)

            if success:
                updated = resource.start()
                await self._repo.save(updated)

                if updated.domain_events:
                    await self._event_bus.publish(list(updated.domain_events))

                return UseCaseResult(
                    success=True,
                    data=ResourceDTO.from_entity(updated).to_dict(),
                )

            return UseCaseResult(success=False, error="Failed to start resource")

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))

    async def stop(self, resource_id: str) -> UseCaseResult:
        try:
            resource_uuid = UUID(resource_id)
            resource = await self._repo.get_by_id(resource_uuid)

            if not resource:
                return UseCaseResult(success=False, error="Resource not found")

            success = await self._resource_port.stop(resource)

            if success:
                updated = resource.stop()
                await self._repo.save(updated)

                if updated.domain_events:
                    await self._event_bus.publish(list(updated.domain_events))

                return UseCaseResult(
                    success=True,
                    data=ResourceDTO.from_entity(updated).to_dict(),
                )

            return UseCaseResult(success=False, error="Failed to stop resource")

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))

    async def terminate(self, resource_id: str) -> UseCaseResult:
        try:
            resource_uuid = UUID(resource_id)
            resource = await self._repo.get_by_id(resource_uuid)

            if not resource:
                return UseCaseResult(success=False, error="Resource not found")

            success = await self._resource_port.terminate(resource)

            if success:
                updated = resource.terminate()
                await self._repo.save(updated)

                if updated.domain_events:
                    await self._event_bus.publish(list(updated.domain_events))

                return UseCaseResult(
                    success=True,
                    data=ResourceDTO.from_entity(updated).to_dict(),
                )

            return UseCaseResult(success=False, error="Failed to terminate resource")

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))


class CreateAgentUseCase:
    def __init__(
        self,
        agent_repo: AgentRepositoryPort,
        event_bus: EventBusPort,
    ):
        self._repo = agent_repo
        self._event_bus = event_bus

    async def execute(
        self,
        name: str,
        description: str,
        provider: str,
        model: str,
        system_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> UseCaseResult:
        try:
            agent = Agent(
                id=uuid4(),
                name=name,
                description=description,
                status=AgentStatus.INACTIVE,
                config=AgentConfig(
                    provider=AIProvider(provider),
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt,
                ),
                capabilities=(),
            )

            saved_agent = await self._repo.save(agent)

            if saved_agent.domain_events:
                await self._event_bus.publish(list(saved_agent.domain_events))

            return UseCaseResult(
                success=True,
                data=AgentDTO.from_entity(saved_agent).to_dict(),
            )

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))


class AnalyzeCostUseCase:
    def __init__(
        self,
        cost_port: CostPort,
        resource_repo: ResourceRepositoryPort,
    ):
        self._cost_port = cost_port
        self._resource_repo = resource_repo

    async def execute(self, provider_id: str) -> UseCaseResult:
        try:
            provider_uuid = UUID(provider_id)

            from datetime import timedelta

            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=30)

            current_cost = await self._cost_port.get_current_cost(
                provider_uuid, start_date, end_date
            )
            cost_breakdown = await self._cost_port.get_cost_breakdown(
                provider_uuid, start_date, end_date
            )
            forecast = await self._cost_port.get_forecast(provider_uuid, 30)

            return UseCaseResult(
                success=True,
                data={
                    "current_month_cost": {
                        "amount": str(current_cost.amount),
                        "currency": current_cost.currency,
                    },
                    "cost_breakdown": cost_breakdown,
                    "monthly_forecast": {
                        "amount": str(forecast.amount),
                        "currency": forecast.currency,
                    },
                    "recommendations": [],
                },
            )

        except Exception as e:
            return UseCaseResult(success=False, error=str(e))
