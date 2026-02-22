"""
Domain Services Tests

Architectural Intent:
- Tests for domain services
- No mocks needed - pure logic tests
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
from domain.value_objects.money import Money
from decimal import Decimal


class TestProviderDomainService:
    @pytest.mark.asyncio
    async def test_get_active_providers(self):
        providers = [
            CloudProvider(
                id=uuid4(),
                provider_type=CloudProviderType.AWS,
                name="aws-1",
                status=ProviderStatus.CONNECTED,
                region="us-east-1",
            ),
            CloudProvider(
                id=uuid4(),
                provider_type=CloudProviderType.AWS,
                name="aws-2",
                status=ProviderStatus.DISCONNECTED,
                region="us-west-2",
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=providers)

        from domain.services.domain_services import ProviderDomainService

        service = ProviderDomainService(mock_repo)

        active = await service.get_active_providers()

        assert len(active) == 1
        assert active[0].name == "aws-1"


class TestResourceDomainService:
    @pytest.mark.asyncio
    async def test_get_running_resources(self):
        resources = [
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.COMPUTE_INSTANCE,
                name="web-server",
                state=ResourceState.RUNNING,
                region="us-east-1",
            ),
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.COMPUTE_INSTANCE,
                name="db-server",
                state=ResourceState.STOPPED,
                region="us-east-1",
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=resources)

        from domain.services.domain_services import ResourceDomainService

        service = ResourceDomainService(mock_repo)

        running = await service.get_running_resources()

        assert len(running) == 1
        assert running[0].name == "web-server"

    @pytest.mark.asyncio
    async def test_get_failed_resources(self):
        resources = [
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.COMPUTE_INSTANCE,
                name="web-server",
                state=ResourceState.FAILED,
                region="us-east-1",
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock(return_value=resources)

        from domain.services.domain_services import ResourceDomainService

        service = ResourceDomainService(mock_repo)

        failed = await service.get_failed_resources()

        assert len(failed) == 1

    def test_calculate_total_cost(self):
        resources = [
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.COMPUTE_INSTANCE,
                name="web-server",
                state=ResourceState.RUNNING,
                region="us-east-1",
            ),
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.DATABASE,
                name="db-server",
                state=ResourceState.RUNNING,
                region="us-east-1",
            ),
            Resource(
                id=uuid4(),
                provider_id=uuid4(),
                resource_type=ResourceType.COMPUTE_INSTANCE,
                name="stopped-server",
                state=ResourceState.STOPPED,
                region="us-east-1",
            ),
        ]

        cost_per_hour = {
            "compute_instance": 0.10,
            "database": 0.50,
        }

        mock_repo = MagicMock()

        from domain.services.domain_services import ResourceDomainService

        service = ResourceDomainService(mock_repo)

        total = service.calculate_total_cost(resources, cost_per_hour)

        assert total.amount == Decimal("0.60")


class TestCostOptimizationService:
    def test_generate_recommendations(self):
        from domain.services.domain_services import CostOptimizationService

        mock_cost_port = MagicMock()
        mock_resource_repo = MagicMock()

        service = CostOptimizationService(mock_cost_port, mock_resource_repo)

        breakdown = {
            "by_service": {
                "compute": Money(Decimal("1500"), "USD"),
                "storage": Money(Decimal("200"), "USD"),
            }
        }

        recommendations = service._generate_recommendations(breakdown)

        assert len(recommendations) == 1
        assert recommendations[0]["service"] == "compute"
        assert "High spending" in recommendations[0]["message"]

    def test_generate_recommendations_no_alerts(self):
        from domain.services.domain_services import CostOptimizationService

        mock_cost_port = MagicMock()
        mock_resource_repo = MagicMock()

        service = CostOptimizationService(mock_cost_port, mock_resource_repo)

        breakdown = {
            "by_service": {
                "storage": Money(Decimal("100"), "USD"),
            }
        }

        recommendations = service._generate_recommendations(breakdown)

        assert len(recommendations) == 0
