"""
Dependency Injection Container

Architectural Intent:
- Wires implementations at composition root
- Following the hexagonal architecture pattern
- Provides all dependencies to MCP servers and use cases
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Callable

from domain.entities.cloud_provider import CloudProviderType
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
from domain.ports.event_bus_port import EventBusPort, DomainEvent
from application.commands.commands import (
    CreateCloudProviderUseCase,
    ConnectProviderUseCase,
    DisconnectProviderUseCase,
    CreateResourceUseCase,
    ManageResourceUseCase,
    CreateAgentUseCase,
    ActivateAgentUseCase,
    DeactivateAgentUseCase,
    AnalyzeCostUseCase,
)
from application.queries.queries import (
    GetCloudProviderQuery,
    ListCloudProvidersQuery,
    GetResourceQuery,
    ListResourcesQuery,
    GetAgentQuery,
    ListAgentsQuery,
)
from infrastructure.adapters.adapters import (
    InMemoryCloudProviderRepository,
    InMemoryResourceRepository,
    InMemoryAgentRepository,
    MockCloudProviderAdapter,
    MockResourceAdapter,
    MockCostAdapter,
    MockObservabilityAdapter,
)
from infrastructure.database.repositories import (
    SQLAlchemyCloudProviderRepository,
    SQLAlchemyResourceRepository,
    SQLAlchemyAgentRepository,
    get_session,
)

logger = logging.getLogger(__name__)


class InMemoryEventBus:
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = {}

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            event_type = type(event)
            if event_type in self._handlers:
                for handler in self._handlers[event_type]:
                    await handler(event)

    async def subscribe(self, event_type: type, handler: Callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def unsubscribe(self, event_type: type, handler: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)


@dataclass
class Container:
    _provider_repo: CloudProviderRepositoryPort = field(
        default_factory=InMemoryCloudProviderRepository
    )
    _resource_repo: ResourceRepositoryPort = field(
        default_factory=InMemoryResourceRepository
    )
    _agent_repo: AgentRepositoryPort = field(default_factory=InMemoryAgentRepository)
    _cloud_provider_adapter: CloudProviderPort = field(
        default_factory=MockCloudProviderAdapter
    )
    _resource_adapter: ResourcePort = field(default_factory=MockResourceAdapter)
    _cost_adapter: CostPort = field(default_factory=MockCostAdapter)
    _observability_adapter: ObservabilityPort = field(
        default_factory=MockObservabilityAdapter
    )
    _event_bus: EventBusPort = field(default_factory=InMemoryEventBus)

    @property
    def provider_repo(self) -> CloudProviderRepositoryPort:
        return self._provider_repo

    @property
    def resource_repo(self) -> ResourceRepositoryPort:
        return self._resource_repo

    @property
    def agent_repo(self) -> AgentRepositoryPort:
        return self._agent_repo

    @property
    def cloud_provider_adapter(self) -> CloudProviderPort:
        return self._cloud_provider_adapter

    @property
    def resource_adapter(self) -> ResourcePort:
        return self._resource_adapter

    @property
    def cost_adapter(self) -> CostPort:
        return self._cost_adapter

    @property
    def observability_adapter(self) -> ObservabilityPort:
        return self._observability_adapter

    @property
    def event_bus(self) -> EventBusPort:
        return self._event_bus

    def create_cloud_provider_use_case(self) -> CreateCloudProviderUseCase:
        return CreateCloudProviderUseCase(
            provider_repo=self._provider_repo,
            event_bus=self._event_bus,
        )

    def create_connect_provider_use_case(self) -> ConnectProviderUseCase:
        return ConnectProviderUseCase(
            provider_repo=self._provider_repo,
            cloud_provider_port=self._cloud_provider_adapter,
            event_bus=self._event_bus,
            resource_repo=self._resource_repo,
            resource_port=self._resource_adapter,
        )

    def create_resource_use_case(self) -> CreateResourceUseCase:
        return CreateResourceUseCase(
            resource_repo=self._resource_repo,
            provider_repo=self._provider_repo,
            resource_port=self._resource_adapter,
            event_bus=self._event_bus,
        )

    def create_manage_resource_use_case(self) -> ManageResourceUseCase:
        return ManageResourceUseCase(
            resource_repo=self._resource_repo,
            resource_port=self._resource_adapter,
            event_bus=self._event_bus,
        )

    def create_agent_use_case(self) -> CreateAgentUseCase:
        return CreateAgentUseCase(
            agent_repo=self._agent_repo,
            event_bus=self._event_bus,
        )

    def create_activate_agent_use_case(self) -> ActivateAgentUseCase:
        return ActivateAgentUseCase(
            agent_repo=self._agent_repo,
            event_bus=self._event_bus,
        )

    def create_deactivate_agent_use_case(self) -> DeactivateAgentUseCase:
        return DeactivateAgentUseCase(
            agent_repo=self._agent_repo,
            event_bus=self._event_bus,
        )

    def create_disconnect_provider_use_case(self) -> DisconnectProviderUseCase:
        return DisconnectProviderUseCase(
            provider_repo=self._provider_repo,
            event_bus=self._event_bus,
        )

    def create_cost_analysis_use_case(self) -> AnalyzeCostUseCase:
        return AnalyzeCostUseCase(
            cost_port=self._cost_adapter,
            resource_repo=self._resource_repo,
        )

    def get_cloud_provider_query(self) -> GetCloudProviderQuery:
        return GetCloudProviderQuery(self._provider_repo)

    def list_cloud_providers_query(self) -> ListCloudProvidersQuery:
        return ListCloudProvidersQuery(self._provider_repo)

    def get_resource_query(self) -> GetResourceQuery:
        return GetResourceQuery(self._resource_repo)

    def list_resources_query(self) -> ListResourcesQuery:
        return ListResourcesQuery(self._resource_repo)

    def get_agent_query(self) -> GetAgentQuery:
        return GetAgentQuery(self._agent_repo)

    def list_agents_query(self) -> ListAgentsQuery:
        return ListAgentsQuery(self._agent_repo)


_container: Container | None = None


def _build_real_cloud_adapters(
    provider_repo: CloudProviderRepositoryPort,
) -> tuple[CloudProviderPort, ResourcePort]:
    """Build dispatch adapters that route to real cloud SDK adapters."""
    from infrastructure.adapters.aws_adapter import AWSCloudProviderAdapter, AWSResourceAdapter
    from infrastructure.adapters.azure_adapter import AzureCloudProviderAdapter, AzureResourceAdapter
    from infrastructure.adapters.gcp_adapter import GCPCloudProviderAdapter, GCPResourceAdapter
    from infrastructure.adapters.dispatch_adapter import DispatchCloudProviderAdapter, DispatchResourceAdapter

    aws_creds = {
        "access_key": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
    }
    aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

    azure_creds = {
        "tenant_id": os.environ.get("AZURE_TENANT_ID", ""),
        "client_id": os.environ.get("AZURE_CLIENT_ID", ""),
        "client_secret": os.environ.get("AZURE_CLIENT_SECRET", ""),
        "subscription_id": os.environ.get("AZURE_SUBSCRIPTION_ID", ""),
    }

    gcp_creds = {
        "project_id": os.environ.get("GCP_PROJECT_ID", ""),
    }

    cloud_adapters: dict[CloudProviderType, CloudProviderPort] = {
        CloudProviderType.AWS: AWSCloudProviderAdapter(aws_creds),
        CloudProviderType.AZURE: AzureCloudProviderAdapter(azure_creds),
        CloudProviderType.GCP: GCPCloudProviderAdapter(gcp_creds),
    }
    resource_adapters: dict[CloudProviderType, ResourcePort] = {
        CloudProviderType.AWS: AWSResourceAdapter(aws_creds),
        CloudProviderType.AZURE: AzureResourceAdapter(azure_creds),
        CloudProviderType.GCP: GCPResourceAdapter(gcp_creds),
    }

    return (
        DispatchCloudProviderAdapter(cloud_adapters),
        DispatchResourceAdapter(resource_adapters, provider_repo),
    )


def get_container() -> Container:
    global _container
    if _container is None:
        session = get_session()
        provider_repo = SQLAlchemyCloudProviderRepository(session)
        resource_repo = SQLAlchemyResourceRepository(session)
        agent_repo = SQLAlchemyAgentRepository(session)

        use_real = os.environ.get("COCKPIT_USE_REAL_CLOUD", "false").lower() in ("true", "1", "yes")

        if use_real:
            logger.info("Using REAL cloud adapters (COCKPIT_USE_REAL_CLOUD=true)")
            cloud_adapter, resource_adapter = _build_real_cloud_adapters(provider_repo)
        else:
            logger.info("Using MOCK cloud adapters (default)")
            cloud_adapter = MockCloudProviderAdapter()
            resource_adapter = MockResourceAdapter()

        _container = Container(
            _provider_repo=provider_repo,
            _resource_repo=resource_repo,
            _agent_repo=agent_repo,
            _cloud_provider_adapter=cloud_adapter,
            _resource_adapter=resource_adapter,
        )
    return _container
