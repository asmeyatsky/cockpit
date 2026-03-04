"""
Google Cloud Platform (GCP) Adapter

Architectural Intent:
- Real GCP implementation using google-cloud
- Implements CloudProviderPort interface
"""

import logging
from uuid import uuid4

from domain.entities.cloud_provider import CloudProvider, ProviderStatus
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort

logger = logging.getLogger(__name__)


class GCPCloudProviderAdapter(CloudProviderPort):
    """GCP implementation of cloud provider operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._project_id = credentials.get("project_id")

    async def connect(self, provider: CloudProvider) -> bool:
        try:
            from google.cloud import compute_v1

            client = compute_v1.InstancesClient()
            client.aggregated_list(request={"project": self._project_id, "max_results": 1})
            return True
        except Exception:
            return False

    async def disconnect(self, provider: CloudProvider) -> bool:
        return True

    async def get_status(self, provider: CloudProvider) -> str:
        try:
            from google.cloud import compute_v1

            client = compute_v1.InstancesClient()
            client.aggregated_list(request={"project": self._project_id, "max_results": 1})
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

    def _map_sql_state(self, state: str) -> ResourceState:
        mapping = {
            "RUNNABLE": ResourceState.RUNNING,
            "PENDING_CREATE": ResourceState.PENDING,
            "MAINTENANCE": ResourceState.RUNNING,
            "SUSPENDED": ResourceState.STOPPED,
            "FAILED": ResourceState.FAILED,
        }
        return mapping.get(state, ResourceState.UNKNOWN)

    async def discover_resources(self, provider: CloudProvider) -> list[Resource]:
        resources: list[Resource] = []
        region = provider.region

        # GCE Instances (aggregated across all zones)
        try:
            from google.cloud import compute_v1

            client = compute_v1.InstancesClient()
            agg = client.aggregated_list(request={"project": self._project_id})
            for zone, response in agg:
                if not response.instances:
                    continue
                for inst in response.instances:
                    zone_name = zone.rsplit("/", 1)[-1] if "/" in zone else zone
                    resources.append(Resource(
                        id=uuid4(),
                        provider_id=provider.id,
                        resource_type=ResourceType.COMPUTE_INSTANCE,
                        name=inst.name,
                        state=self._map_instance_state(inst.status),
                        region=zone_name,
                        arn=inst.self_link,
                        metadata=(
                            ("machine_type", (inst.machine_type or "").rsplit("/", 1)[-1]),
                            ("zone", zone_name),
                        ),
                    ))
        except Exception as e:
            logger.warning("GCP GCE discovery failed: %s", e)

        # GCS Buckets
        try:
            from google.cloud import storage

            storage_client = storage.Client(project=self._project_id)
            for bucket in storage_client.list_buckets():
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.STORAGE_BUCKET,
                    name=bucket.name,
                    state=ResourceState.RUNNING,
                    region=bucket.location or region,
                    arn=f"gs://{bucket.name}",
                    metadata=(
                        ("storage_class", bucket.storage_class or ""),
                        ("location", bucket.location or ""),
                    ),
                ))
        except Exception as e:
            logger.warning("GCP GCS discovery failed: %s", e)

        # Cloud SQL Instances
        try:
            from googleapiclient.discovery import build

            service = build("sqladmin", "v1beta4")
            resp = service.instances().list(project=self._project_id).execute()
            for db in resp.get("items", []):
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.DATABASE,
                    name=db["name"],
                    state=self._map_sql_state(db.get("state", "")),
                    region=db.get("region", region),
                    arn=db.get("selfLink"),
                    metadata=(
                        ("database_version", db.get("databaseVersion", "")),
                        ("tier", db.get("settings", {}).get("tier", "")),
                    ),
                ))
        except Exception as e:
            logger.warning("GCP Cloud SQL discovery failed: %s", e)

        # Cloud Functions (v2)
        try:
            from google.cloud.functions_v2 import FunctionServiceClient, ListFunctionsRequest

            functions_client = FunctionServiceClient()
            parent = f"projects/{self._project_id}/locations/-"
            request = ListFunctionsRequest(parent=parent)
            for fn in functions_client.list_functions(request=request):
                fn_state = ResourceState.RUNNING if fn.state.name == "ACTIVE" else ResourceState.PENDING
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.SERVERLESS_FUNCTION,
                    name=fn.name.rsplit("/", 1)[-1],
                    state=fn_state,
                    region=fn.name.split("/locations/")[1].split("/")[0] if "/locations/" in fn.name else region,
                    arn=fn.name,
                    metadata=(
                        ("runtime", getattr(fn.build_config, "runtime", "") or ""),
                    ),
                ))
        except Exception as e:
            logger.warning("GCP Cloud Functions discovery failed: %s", e)

        # VPC Networks
        try:
            from google.cloud import compute_v1

            networks_client = compute_v1.NetworksClient()
            for net in networks_client.list(project=self._project_id):
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.NETWORK_VPC,
                    name=net.name,
                    state=ResourceState.RUNNING,
                    region="global",
                    arn=net.self_link,
                    metadata=(
                        ("auto_create_subnetworks", str(getattr(net, "auto_create_subnetworks", ""))),
                    ),
                ))
        except Exception as e:
            logger.warning("GCP VPC discovery failed: %s", e)

        # URL Maps (Load Balancers)
        try:
            from google.cloud import compute_v1

            url_maps_client = compute_v1.UrlMapsClient()
            for um in url_maps_client.list(project=self._project_id):
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.LOAD_BALANCER,
                    name=um.name,
                    state=ResourceState.RUNNING,
                    region="global",
                    arn=um.self_link,
                ))
        except Exception as e:
            logger.warning("GCP URL Maps discovery failed: %s", e)

        # Memorystore (Redis) Instances
        try:
            from google.cloud import redis_v1

            redis_client = redis_v1.CloudRedisClient()
            parent = f"projects/{self._project_id}/locations/-"
            for instance in redis_client.list_instances(parent=parent):
                redis_state = ResourceState.RUNNING if instance.state.name == "READY" else ResourceState.PENDING
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.CACHE,
                    name=instance.name.rsplit("/", 1)[-1],
                    state=redis_state,
                    region=instance.location_id or region,
                    arn=instance.name,
                    metadata=(
                        ("tier", instance.tier.name if instance.tier else ""),
                        ("memory_size_gb", str(instance.memory_size_gb)),
                    ),
                ))
        except Exception as e:
            logger.warning("GCP Memorystore discovery failed: %s", e)

        logger.info("GCP discovery found %d resources", len(resources))
        return resources

    async def create(self, provider: CloudProvider, config: dict) -> Resource:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        instance_name = config.get("name", "new-instance")
        zone = config.get("zone", provider.region)
        machine_type = config.get("machine_type", f"zones/{zone}/machineTypes/e2-medium")
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

        _wait_for_operation(operation)

        return Resource(
            id=uuid4(),
            provider_id=provider.id,
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name=instance_name,
            state=ResourceState.PENDING,
            region=zone,
            arn=f"projects/{self._project_id}/zones/{zone}/instances/{instance_name}",
            tags=tuple((k, v) for k, v in (config.get("tags") or {}).items()),
        )

    async def start(self, resource: Resource) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        operation = client.start(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.name),
        )

        _wait_for_operation(operation)
        return True

    async def stop(self, resource: Resource) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        operation = client.stop(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.name),
        )

        _wait_for_operation(operation)
        return True

    async def terminate(self, resource: Resource) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        operation = client.delete(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.name),
        )

        _wait_for_operation(operation)
        return True

    async def get_status(self, resource: Resource) -> str:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        instance = client.get(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.name),
        )

        return instance.status.lower()

    async def update_tags(self, resource: Resource, tags: dict) -> bool:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()

        instance = client.get(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.name),
        )

        # GCP uses labels (key-value) rather than tags (keys only)
        labels = dict(instance.labels or {})
        labels.update(tags)
        request = compute_v1.SetLabelsInstanceRequest(
            project=self._project_id,
            zone=resource.region,
            instance=str(resource.name),
            instances_set_labels_request_resource=compute_v1.InstancesSetLabelsRequest(
                label_fingerprint=instance.label_fingerprint,
                labels=labels,
            ),
        )
        operation = client.set_labels(request=request)
        _wait_for_operation(operation)
        return True


def _wait_for_operation(operation) -> None:
    result = operation.result()
    if hasattr(operation, "error_code") and operation.error_code:
        raise Exception(f"Operation failed: {operation.error_message}")
    return result
