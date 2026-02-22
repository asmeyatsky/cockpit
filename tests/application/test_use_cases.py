"""
Application Tests - Use Cases

Architectural Intent:
- Comprehensive use case tests with mocked ports
- Following Rule 4: Mandatory Testing Coverage
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.entities.agent import Agent, AgentConfig, AIProvider, AgentStatus
from domain.ports.repository_ports import (
    CloudProviderRepositoryPort,
    ResourceRepositoryPort,
    AgentRepositoryPort,
)
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort
from domain.ports.event_bus_port import EventBusPort
from application.commands.commands import (
    CreateCloudProviderUseCase,
    ConnectProviderUseCase,
    CreateResourceUseCase,
    ManageResourceUseCase,
    CreateAgentUseCase,
    AnalyzeCostUseCase,
    UseCaseResult,
)
from application.queries.queries import (
    GetCloudProviderQuery,
    ListCloudProvidersQuery,
    GetResourceQuery,
    ListResourcesQuery,
    GetAgentQuery,
    ListAgentsQuery,
)


class TestCreateCloudProviderUseCase:
    @pytest.mark.asyncio
    async def test_create_provider_with_valid_data(self):
        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_event_bus = AsyncMock(spec=EventBusPort)

        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
            account_id="123456789",
        )
        mock_repo.save.return_value = provider

        use_case = CreateCloudProviderUseCase(
            provider_repo=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(
            provider_type="aws",
            name="aws-prod",
            region="us-east-1",
            account_id="123456789",
        )

        assert result.success is True
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_provider_database_error(self):
        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_event_bus = AsyncMock(spec=EventBusPort)
        mock_repo.save.side_effect = Exception("Database error")

        use_case = CreateCloudProviderUseCase(
            provider_repo=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(
            provider_type="aws",
            name="aws-prod",
            region="us-east-1",
        )

        assert result.success is False
        assert "Database error" in result.error


class TestConnectProviderUseCase:
    @pytest.mark.asyncio
    async def test_connect_provider_success(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
        )

        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_repo.get_by_id.return_value = provider
        mock_repo.save.return_value = provider.connect()

        mock_cloud = AsyncMock(spec=CloudProviderPort)
        mock_cloud.connect.return_value = True

        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = ConnectProviderUseCase(
            provider_repo=mock_repo,
            cloud_provider_port=mock_cloud,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(str(provider.id))

        assert result.success is True
        mock_cloud.connect.assert_awaited_once()
        mock_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_provider_not_found(self):
        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_repo.get_by_id.return_value = None

        mock_cloud = AsyncMock(spec=CloudProviderPort)
        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = ConnectProviderUseCase(
            provider_repo=mock_repo,
            cloud_provider_port=mock_cloud,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(str(uuid4()))

        assert result.success is False
        assert "not found" in result.error


class TestCreateResourceUseCase:
    @pytest.mark.asyncio
    async def test_create_resource_success(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )

        resource = Resource(
            id=uuid4(),
            provider_id=provider.id,
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        mock_resource_repo = AsyncMock(spec=ResourceRepositoryPort)
        mock_provider_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_provider_repo.get_by_id.return_value = provider

        mock_resource_port = AsyncMock(spec=ResourcePort)
        mock_resource_port.create.return_value = resource

        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = CreateResourceUseCase(
            resource_repo=mock_resource_repo,
            provider_repo=mock_provider_repo,
            resource_port=mock_resource_port,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(
            provider_id=str(provider.id),
            resource_type="compute_instance",
            name="web-server",
            region="us-east-1",
            config={},
        )

        assert result.success is True
        mock_resource_port.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_resource_provider_not_found(self):
        mock_resource_repo = AsyncMock(spec=ResourceRepositoryPort)
        mock_provider_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_provider_repo.get_by_id.return_value = None
        mock_resource_port = AsyncMock(spec=ResourcePort)
        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = CreateResourceUseCase(
            resource_repo=mock_resource_repo,
            provider_repo=mock_provider_repo,
            resource_port=mock_resource_port,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(
            provider_id=str(uuid4()),
            resource_type="compute_instance",
            name="web-server",
            region="us-east-1",
            config={},
        )

        assert result.success is False
        assert "not found" in result.error


class TestManageResourceUseCase:
    @pytest.mark.asyncio
    async def test_start_resource_success(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.STOPPED,
            region="us-east-1",
        )

        mock_repo = AsyncMock(spec=ResourceRepositoryPort)
        mock_repo.get_by_id.return_value = resource
        mock_repo.save.return_value = resource.start()

        mock_resource_port = AsyncMock(spec=ResourcePort)
        mock_resource_port.start.return_value = True

        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = ManageResourceUseCase(
            resource_repo=mock_repo,
            resource_port=mock_resource_port,
            event_bus=mock_event_bus,
        )

        result = await use_case.start(str(resource.id))

        assert result.success is True
        mock_resource_port.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_resource_success(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        mock_repo = AsyncMock(spec=ResourceRepositoryPort)
        mock_repo.get_by_id.return_value = resource
        mock_repo.save.return_value = resource.stop()

        mock_resource_port = AsyncMock(spec=ResourcePort)
        mock_resource_port.stop.return_value = True

        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = ManageResourceUseCase(
            resource_repo=mock_repo,
            resource_port=mock_resource_port,
            event_bus=mock_event_bus,
        )

        result = await use_case.stop(str(resource.id))

        assert result.success is True

    @pytest.mark.asyncio
    async def test_terminate_resource_success(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        mock_repo = AsyncMock(spec=ResourceRepositoryPort)
        mock_repo.get_by_id.return_value = resource
        mock_repo.save.return_value = resource.terminate()

        mock_resource_port = AsyncMock(spec=ResourcePort)
        mock_resource_port.terminate.return_value = True

        mock_event_bus = AsyncMock(spec=EventBusPort)

        use_case = ManageResourceUseCase(
            resource_repo=mock_repo,
            resource_port=mock_resource_port,
            event_bus=mock_event_bus,
        )

        result = await use_case.terminate(str(resource.id))

        assert result.success is True


class TestCreateAgentUseCase:
    @pytest.mark.asyncio
    async def test_create_agent_success(self):
        mock_repo = AsyncMock(spec=AgentRepositoryPort)
        mock_event_bus = AsyncMock(spec=EventBusPort)

        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.INACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
                max_tokens=4096,
                temperature=0.7,
                system_prompt="You are a helpful assistant",
            ),
            capabilities=(),
        )
        mock_repo.save.return_value = agent

        use_case = CreateAgentUseCase(
            agent_repo=mock_repo,
            event_bus=mock_event_bus,
        )

        result = await use_case.execute(
            name="test-agent",
            description="A test agent",
            provider="claude",
            model="claude-3-5-sonnet",
            system_prompt="You are a helpful assistant",
        )

        assert result.success is True
        mock_repo.save.assert_awaited_once()


class TestAnalyzeCostUseCase:
    @pytest.mark.asyncio
    async def test_analyze_cost_success(self):
        from domain.value_objects.money import Money
        from decimal import Decimal
        from datetime import datetime, timedelta, UTC

        mock_cost_port = AsyncMock()
        mock_cost_port.get_current_cost.return_value = Money(Decimal("1000"), "USD")
        mock_cost_port.get_cost_breakdown.return_value = {"by_service": {}}
        mock_cost_port.get_forecast.return_value = Money(Decimal("1500"), "USD")

        mock_resource_repo = AsyncMock(spec=ResourceRepositoryPort)

        use_case = AnalyzeCostUseCase(
            cost_port=mock_cost_port,
            resource_repo=mock_resource_repo,
        )

        result = await use_case.execute(str(uuid4()))

        assert result.success is True
        assert "current_month_cost" in result.data


class TestQueryHandlers:
    @pytest.mark.asyncio
    async def test_get_cloud_provider_query(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )

        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_repo.get_by_id.return_value = provider

        query = GetCloudProviderQuery(mock_repo)
        result = await query.execute(str(provider.id))

        assert result is not None
        assert result.name == "aws-prod"

    @pytest.mark.asyncio
    async def test_get_cloud_provider_not_found(self):
        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_repo.get_by_id.return_value = None

        query = GetCloudProviderQuery(mock_repo)
        result = await query.execute(str(uuid4()))

        assert result is None

    @pytest.mark.asyncio
    async def test_list_cloud_providers_query(self):
        providers = [
            CloudProvider(
                id=uuid4(),
                provider_type=CloudProviderType.AWS,
                name="aws-prod",
                status=ProviderStatus.CONNECTED,
                region="us-east-1",
            ),
            CloudProvider(
                id=uuid4(),
                provider_type=CloudProviderType.AZURE,
                name="azure-prod",
                status=ProviderStatus.DISCONNECTED,
                region="eastus",
            ),
        ]

        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_repo.get_all.return_value = providers

        query = ListCloudProvidersQuery(mock_repo)
        result = await query.execute()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_resources_query_with_filters(self):
        resources = [
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.COMPUTE_INSTANCE,
                name="web-server",
                state=ResourceState.RUNNING,
                region="us-east-1",
            ),
        ]

        mock_repo = AsyncMock(spec=ResourceRepositoryPort)
        mock_repo.get_all.return_value = resources

        query = ListResourcesQuery(mock_repo)
        result = await query.execute(state="running")

        assert len(result) == 1


class TestUseCaseResult:
    def test_success_result_with_data(self):
        result = UseCaseResult(success=True, data={"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result_with_error(self):
        result = UseCaseResult(success=False, error="Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_result_to_dict(self):
        result = UseCaseResult(success=True, data={"id": "123"})

        assert result.success is True
        assert "id" in result.data
