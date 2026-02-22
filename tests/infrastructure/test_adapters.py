"""
Infrastructure Tests - Adapters

Architectural Intent:
- Integration tests for infrastructure adapters
- Following Rule 4: Mandatory Testing Coverage
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
)
from domain.entities.resource import Resource, ResourceType, ResourceState
from infrastructure.adapters.adapters import (
    InMemoryCloudProviderRepository,
    InMemoryResourceRepository,
    InMemoryAgentRepository,
    MockCloudProviderAdapter,
    MockResourceAdapter,
)


class TestInMemoryCloudProviderRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self):
        repo = InMemoryCloudProviderRepository()
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="test-provider",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
        )

        saved = await repo.save(provider)
        retrieved = await repo.get_by_id(provider.id)

        assert saved == provider
        assert retrieved == provider

    @pytest.mark.asyncio
    async def test_get_all(self):
        repo = InMemoryCloudProviderRepository()

        provider1 = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )
        provider2 = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AZURE,
            name="azure",
            status=ProviderStatus.DISCONNECTED,
            region="eastus",
        )

        await repo.save(provider1)
        await repo.save(provider2)

        all_providers = await repo.get_all()

        assert len(all_providers) == 2


class TestInMemoryResourceRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self):
        repo = InMemoryResourceRepository()
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="test-resource",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        saved = await repo.save(resource)
        retrieved = await repo.get_by_id(resource.id)

        assert saved == resource
        assert retrieved == resource

    @pytest.mark.asyncio
    async def test_get_by_provider(self):
        repo = InMemoryResourceRepository()
        provider_id = uuid4()

        resource1 = Resource(
            id=uuid4(),
            provider_id=provider_id,
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="resource-1",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )
        resource2 = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.STORAGE_BUCKET,
            name="resource-2",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        await repo.save(resource1)
        await repo.save(resource2)

        resources = await repo.get_by_provider(provider_id)

        assert len(resources) == 1
        assert resources[0].name == "resource-1"


class TestMockAdapters:
    @pytest.mark.asyncio
    async def test_cloud_provider_adapter_connect(self):
        adapter = MockCloudProviderAdapter()
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="test",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
        )

        result = await adapter.connect(provider)

        assert result is True

    @pytest.mark.asyncio
    async def test_resource_adapter_create(self):
        adapter = MockResourceAdapter()
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="test",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )

        resource = await adapter.create(
            provider,
            {"name": "new-resource", "resource_type": ResourceType.COMPUTE_INSTANCE},
        )

        assert resource.name == "new-resource"
        assert resource.state == ResourceState.RUNNING
