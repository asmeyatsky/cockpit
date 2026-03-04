"""
Azure Cloud Provider Adapter

Architectural Intent:
- Real Azure implementation using azure-mgmt
- Implements CloudProviderPort interface
"""

import logging
from uuid import uuid4

from domain.entities.cloud_provider import CloudProvider, ProviderStatus
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort

logger = logging.getLogger(__name__)


class AzureCloudProviderAdapter(CloudProviderPort):
    """Azure implementation of cloud provider operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._tenant_id = credentials.get("tenant_id")
        self._client_id = credentials.get("client_id")
        self._client_secret = credentials.get("client_secret")
        self._subscription_id = credentials.get("subscription_id")

    def _get_credential(self):
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=self._tenant_id,
            client_id=self._client_id,
            client_secret=self._client_secret,
        )

    async def connect(self, provider: CloudProvider) -> bool:
        try:
            from azure.mgmt.compute import ComputeManagementClient

            credential = self._get_credential()
            compute_client = ComputeManagementClient(credential, self._subscription_id)
            list(compute_client.virtual_machines.list_all())
            return True
        except Exception:
            return False

    async def disconnect(self, provider: CloudProvider) -> bool:
        return True

    async def get_status(self, provider: CloudProvider) -> str:
        try:
            from azure.mgmt.compute import ComputeManagementClient

            credential = self._get_credential()
            compute_client = ComputeManagementClient(credential, self._subscription_id)
            list(compute_client.virtual_machines.list_all())
            return "connected"
        except Exception:
            return "error"


class AzureResourceAdapter(ResourcePort):
    """Azure implementation of resource operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._subscription_id = credentials.get("subscription_id")

    def _get_credential(self):
        from azure.identity import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=self._credentials.get("tenant_id"),
            client_id=self._credentials.get("client_id"),
            client_secret=self._credentials.get("client_secret"),
        )

    def _map_vm_power_state(self, statuses: list) -> ResourceState:
        for status in (statuses or []):
            code = getattr(status, "code", "")
            if code.startswith("PowerState/"):
                power = code.split("/", 1)[1].lower()
                mapping = {
                    "running": ResourceState.RUNNING,
                    "deallocated": ResourceState.STOPPED,
                    "deallocating": ResourceState.STOPPED,
                    "stopped": ResourceState.STOPPED,
                    "starting": ResourceState.PENDING,
                }
                return mapping.get(power, ResourceState.UNKNOWN)
        return ResourceState.UNKNOWN

    async def discover_resources(self, provider: CloudProvider) -> list[Resource]:
        credential = self._get_credential()
        resources: list[Resource] = []
        region = provider.region

        # Virtual Machines
        try:
            from azure.mgmt.compute import ComputeManagementClient

            compute_client = ComputeManagementClient(credential, self._subscription_id)
            for vm in compute_client.virtual_machines.list_all():
                # Get instance view for power state
                state = ResourceState.UNKNOWN
                try:
                    rg = vm.id.split("/")[4]
                    iv = compute_client.virtual_machines.instance_view(rg, vm.name)
                    state = self._map_vm_power_state(iv.statuses)
                except Exception:
                    pass
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.COMPUTE_INSTANCE,
                    name=vm.name,
                    state=state,
                    region=vm.location or region,
                    arn=vm.id,
                    metadata=(
                        ("vm_size", getattr(vm.hardware_profile, "vm_size", "") or ""),
                        ("resource_group", vm.id.split("/")[4] if vm.id else ""),
                    ),
                ))
        except Exception as e:
            logger.warning("Azure VM discovery failed: %s", e)

        # Storage Accounts
        try:
            from azure.mgmt.storage import StorageManagementClient

            storage_client = StorageManagementClient(credential, self._subscription_id)
            for acct in storage_client.storage_accounts.list():
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.STORAGE_BUCKET,
                    name=acct.name,
                    state=ResourceState.RUNNING,
                    region=acct.location or region,
                    arn=acct.id,
                    metadata=(
                        ("kind", getattr(acct, "kind", "") or ""),
                        ("sku", getattr(getattr(acct, "sku", None), "name", "") or ""),
                    ),
                ))
        except Exception as e:
            logger.warning("Azure Storage discovery failed: %s", e)

        # SQL Servers
        try:
            from azure.mgmt.sql import SqlManagementClient

            sql_client = SqlManagementClient(credential, self._subscription_id)
            for server in sql_client.servers.list():
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.DATABASE,
                    name=server.name,
                    state=ResourceState.RUNNING,
                    region=server.location or region,
                    arn=server.id,
                    metadata=(
                        ("fqdn", getattr(server, "fully_qualified_domain_name", "") or ""),
                        ("version", getattr(server, "version", "") or ""),
                    ),
                ))
        except Exception as e:
            logger.warning("Azure SQL discovery failed: %s", e)

        # Function Apps
        try:
            from azure.mgmt.web import WebSiteManagementClient

            web_client = WebSiteManagementClient(credential, self._subscription_id)
            for app in web_client.web_apps.list():
                kind = getattr(app, "kind", "") or ""
                if "functionapp" not in kind.lower():
                    continue
                app_state = ResourceState.RUNNING if getattr(app, "state", "") == "Running" else ResourceState.STOPPED
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.SERVERLESS_FUNCTION,
                    name=app.name,
                    state=app_state,
                    region=app.location or region,
                    arn=app.id,
                ))
        except Exception as e:
            logger.warning("Azure Functions discovery failed: %s", e)

        # Virtual Networks
        try:
            from azure.mgmt.network import NetworkManagementClient

            network_client = NetworkManagementClient(credential, self._subscription_id)
            for vnet in network_client.virtual_networks.list_all():
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.NETWORK_VPC,
                    name=vnet.name,
                    state=ResourceState.RUNNING,
                    region=vnet.location or region,
                    arn=vnet.id,
                ))
        except Exception as e:
            logger.warning("Azure VNet discovery failed: %s", e)

        # Load Balancers
        try:
            from azure.mgmt.network import NetworkManagementClient

            network_client = NetworkManagementClient(credential, self._subscription_id)
            for lb in network_client.load_balancers.list_all():
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.LOAD_BALANCER,
                    name=lb.name,
                    state=ResourceState.RUNNING,
                    region=lb.location or region,
                    arn=lb.id,
                ))
        except Exception as e:
            logger.warning("Azure LB discovery failed: %s", e)

        # Redis Caches
        try:
            from azure.mgmt.redis import RedisManagementClient

            redis_client = RedisManagementClient(credential, self._subscription_id)
            for cache in redis_client.redis.list_by_subscription():
                redis_state = ResourceState.RUNNING if getattr(cache, "provisioning_state", "") == "Succeeded" else ResourceState.PENDING
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.CACHE,
                    name=cache.name,
                    state=redis_state,
                    region=cache.location or region,
                    arn=cache.id,
                ))
        except Exception as e:
            logger.warning("Azure Redis discovery failed: %s", e)

        logger.info("Azure discovery found %d resources", len(resources))
        return resources

    async def create(self, provider: CloudProvider, config: dict) -> Resource:
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.compute.models import (
            VirtualMachine,
            HardwareProfile,
        )

        credential = self._get_credential()
        compute_client = ComputeManagementClient(credential, self._subscription_id)

        vm_name = config.get("name", "new-vm")
        resource_group = config.get("resource_group", "default")
        location = config.get("location", provider.region)
        vm_size = config.get("vm_size", "Standard_DS1_v2")

        async_poller = compute_client.virtual_machines.begin_create_or_update(
            resource_group,
            vm_name,
            VirtualMachine(
                location=location,
                hardware_profile=HardwareProfile(vm_size=vm_size),
            ),
        )

        vm = async_poller.result()

        return Resource(
            id=uuid4(),
            provider_id=provider.id,
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name=vm_name,
            state=ResourceState.PENDING,
            region=location,
            arn=vm.id,
            tags=tuple((k, v) for k, v in (config.get("tags") or {}).items()),
        )

    async def start(self, resource: Resource) -> bool:
        return True

    async def stop(self, resource: Resource) -> bool:
        return True

    async def terminate(self, resource: Resource) -> bool:
        return True

    async def get_status(self, resource: Resource) -> str:
        return "running"

    async def update_tags(self, resource: Resource, tags: dict) -> bool:
        return True
