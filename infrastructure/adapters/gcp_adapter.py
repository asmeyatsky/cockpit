"""
Google Cloud Platform (GCP) Adapter

Architectural Intent:
- Real GCP implementation using google-cloud
- Implements CloudProviderPort interface
"""

from typing import Optional
from uuid import UUID

from domain.entities.cloud_provider import CloudProvider, ProviderStatus
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort


class GCPCloudProviderAdapter(CloudProviderPort):
    """GCP implementation of cloud provider operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._project_id = credentials.get("project_id")

    async def connect(self, provider: CloudProvider) -> bool:
        try:
            from google.cloud import compute_v1

            client = compute_v1.InstancesClient()
            client.list(project=self._project_id, zone=provider.region)
            return True
        except Exception:
            return False

    async def disconnect(self, provider: CloudProvider) -> bool:
        return True

    async def get_status(self, provider: CloudProvider) -> str:
        try:
            from google.cloud import compute_v1

            client = compute_v1.InstancesClient()
            client.list(project=self._project_id, zone=provider.region)
            return "connected"
        except Exception:
            return "error"


class GCPResourceAdapter(ResourcePort):
    """GCP implementation of resource operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._project_id = credentials.get("project_id")

    def _map_instance_state(self, status: str) -> ResourceState:
        mapping = {
            "PROVISIONING": ResourceState.PENDING,
            "STAGING": ResourceState.PENDING,
            "RUNNING": ResourceState.RUNNING,
            "STOPPING": ResourceState.STOPPED,
            "SUSPENDED": ResourceState.STOPPED,
            "TERMINATED": ResourceState.TERMINATED,
        }
        return mapping.get(status, ResourceState.UNKNOWN)

    async def create(self, provider: CloudProvider, config: dict) -> Resource:
        from google.cloud import compute_v1
        from google.api_core.extended_operation import ExtendedOperation

        client = compute_v1.InstancesClient()

        instance_name = config.get("name", "new-instance")
        zone = config.get("zone", provider.region)
        machine_type = config.get("machine_type", f"zones/{zone}/machineType/e2-medium")
        image = config.get(
            "image", "projects/debian-cloud/global/images/debian-11-bullseye-v20230509"
        )

        instance = compute_v1.Instance(
            name=instance_name,
            machine_type=machine_type,
            disks=[
                compute_v1.AttachedDisk(
                    initialize_params=compute_v1.AttachedDiskInitializeParams(
                        source_image=image,
                    ),
                    boot=True,
                    auto_delete=True,
                )
            ],
            network_interfaces=[
                compute_v1.NetworkInterface(
                    network="global/networks/default",
                )
            ],
        )

        operation = client.insert(
            project=self._project_id,
            zone=zone,
            instance_resource=instance,
        )

        wait_for_operation(operation, client)

        return Resource(
            id=instance_name,
            provider_id=provider.id,
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name=instance_name,
            state=ResourceState.PENDING,
            region=zone,
            arn=f"projects/{self._project_id}/zones/{zone}/instances/{instance_name}",
            tags=config.get("tags", {}),
        )

    async def start(self, resource: Resource) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()
        zone = resource.region

        operation = client.start(
            project=self._project_id,
            zone=zone,
            instance=str(resource.id),
        )

        wait_for_operation(operation, client)
        return True

    async def stop(self, resource: Resource) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()
        zone = resource.region

        operation = client.stop(
            project=self._project_id,
            zone=zone,
            instance=str(resource.id),
        )

        wait_for_operation(operation, client)
        return True

    async def terminate(self, resource: Resource) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()
        zone = resource.region

        operation = client.delete(
            project=self._project_id,
            zone=zone,
            instance=str(resource.id),
        )

        wait_for_operation(operation, client)
        return True

    async def get_status(self, resource: Resource) -> str:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        instance = client.get(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.id),
        )

        return instance.status.name.lower()

    async def update_tags(self, resource: Resource, tags: dict) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        instance = client.get(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.id),
        )

        instance.tags.items = [f"{k}={v}" for k, v in tags.items()]

        client.set_tags(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.id),
            instance_resource=instance,
        )

        return True


def wait_for_operation(operation: ExtendedOperation, client) -> None:
    from google.api_core.extended_operation import ExtendedOperation

    result = operation.result()
    if operation.error_code:
        raise Exception(f"Operation failed: {operation.error_message}")
    return result
