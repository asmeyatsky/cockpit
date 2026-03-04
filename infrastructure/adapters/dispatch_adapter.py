"""
Dispatch Adapters

Routes CloudProviderPort and ResourcePort calls to the correct
cloud-specific adapter based on provider type.
"""

import logging
from uuid import UUID

from domain.entities.cloud_provider import CloudProvider, CloudProviderType
from domain.entities.resource import Resource
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort
from domain.ports.repository_ports import CloudProviderRepositoryPort

logger = logging.getLogger(__name__)


class DispatchCloudProviderAdapter(CloudProviderPort):
    """Routes cloud provider operations to the correct adapter based on provider_type."""

    def __init__(self, adapters: dict[CloudProviderType, CloudProviderPort]):
        self._adapters = adapters

    def _get_adapter(self, provider: CloudProvider) -> CloudProviderPort:
        adapter = self._adapters.get(provider.provider_type)
        if adapter is None:
            raise ValueError(f"No adapter registered for provider type: {provider.provider_type}")
        return adapter

    async def connect(self, provider: CloudProvider) -> bool:
        return await self._get_adapter(provider).connect(provider)

    async def disconnect(self, provider: CloudProvider) -> bool:
        return await self._get_adapter(provider).disconnect(provider)

    async def get_status(self, provider: CloudProvider) -> str:
        return await self._get_adapter(provider).get_status(provider)


class DispatchResourceAdapter(ResourcePort):
    """Routes resource operations to the correct adapter based on provider type.

    For methods that receive a Resource, the provider_id is looked up in the
    provider repository to determine the correct adapter.
    """

    def __init__(
        self,
        adapters: dict[CloudProviderType, ResourcePort],
        provider_repo: CloudProviderRepositoryPort,
    ):
        self._adapters = adapters
        self._provider_repo = provider_repo

    def _get_adapter_for_type(self, provider_type: CloudProviderType) -> ResourcePort:
        adapter = self._adapters.get(provider_type)
        if adapter is None:
            raise ValueError(f"No resource adapter registered for provider type: {provider_type}")
        return adapter

    async def _get_adapter_for_resource(self, resource: Resource) -> ResourcePort:
        provider = await self._provider_repo.get_by_id(resource.provider_id)
        if provider is None:
            raise ValueError(f"Provider not found for resource: {resource.id}")
        return self._get_adapter_for_type(provider.provider_type)

    async def create(self, provider: CloudProvider, config: dict) -> Resource:
        return await self._get_adapter_for_type(provider.provider_type).create(provider, config)

    async def discover_resources(self, provider: CloudProvider) -> list[Resource]:
        return await self._get_adapter_for_type(provider.provider_type).discover_resources(provider)

    async def start(self, resource: Resource) -> bool:
        adapter = await self._get_adapter_for_resource(resource)
        return await adapter.start(resource)

    async def stop(self, resource: Resource) -> bool:
        adapter = await self._get_adapter_for_resource(resource)
        return await adapter.stop(resource)

    async def terminate(self, resource: Resource) -> bool:
        adapter = await self._get_adapter_for_resource(resource)
        return await adapter.terminate(resource)

    async def get_status(self, resource: Resource) -> str:
        adapter = await self._get_adapter_for_resource(resource)
        return await adapter.get_status(resource)

    async def update_tags(self, resource: Resource, tags: dict) -> bool:
        adapter = await self._get_adapter_for_resource(resource)
        return await adapter.update_tags(resource, tags)
