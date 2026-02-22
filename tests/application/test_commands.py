"""
Application Tests - Use Cases

Architectural Intent:
- Use case tests with mocked ports
- Following Rule 4: Mandatory Testing Coverage
- Verifies orchestration logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.ports.repository_ports import CloudProviderRepositoryPort
from domain.ports.event_bus_port import EventBusPort
from application.commands.commands import CreateCloudProviderUseCase, UseCaseResult
from application.dtos.dtos import CloudProviderDTO


class TestCreateCloudProviderUseCase:
    @pytest.mark.asyncio
    async def test_create_provider_success(self):
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
        mock_event_bus.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_provider_failure(self):
        mock_repo = AsyncMock(spec=CloudProviderRepositoryPort)
        mock_repo.save.side_effect = Exception("Database error")
        mock_event_bus = AsyncMock(spec=EventBusPort)

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


class TestUseCaseResult:
    def test_success_result(self):
        result = UseCaseResult(success=True, data={"key": "value"})

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result(self):
        result = UseCaseResult(success=False, error="Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None
