"""
AWS Cloud Provider Adapter

Architectural Intent:
- Real AWS implementation using boto3
- Implements CloudProviderPort interface
- Following Rule 2: Interface-First Development
"""

import logging
import boto3
from datetime import datetime
from uuid import UUID, uuid4

from domain.entities.cloud_provider import CloudProvider, ProviderStatus
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort

logger = logging.getLogger(__name__)


class AWSCloudProviderAdapter(CloudProviderPort):
    """AWS implementation of cloud provider operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._clients: dict = {}

    def _get_client(self, service: str, region: str):
        key = f"{service}-{region}"
        if key not in self._clients:
            self._clients[key] = boto3.client(
                service,
                region_name=region,
                aws_access_key_id=self._credentials.get("access_key"),
                aws_secret_access_key=self._credentials.get("secret_key"),
            )
        return self._clients[key]

    async def connect(self, provider: CloudProvider) -> bool:
        try:
            ec2 = self._get_client("ec2", provider.region)
            ec2.describe_instances()
            return True
        except Exception:
            return False

    async def disconnect(self, provider: CloudProvider) -> bool:
        return True

    async def get_status(self, provider: CloudProvider) -> str:
        try:
            ec2 = self._get_client("ec2", provider.region)
            ec2.describe_instances()
            return "connected"
        except Exception:
            return "error"


class AWSResourceAdapter(ResourcePort):
    """AWS implementation of resource operations."""

    def __init__(self, credentials: dict):
        self._credentials = credentials
        self._clients: dict = {}

    def _get_service_client(self, service: str, region: str):
        key = f"{service}-{region}"
        if key not in self._clients:
            self._clients[key] = boto3.client(
                service,
                region_name=region,
                aws_access_key_id=self._credentials.get("access_key"),
                aws_secret_access_key=self._credentials.get("secret_key"),
            )
        return self._clients[key]

    def _get_client(self, region: str):
        return self._get_service_client("ec2", region)

    def _map_instance_state(self, state: str) -> ResourceState:
        mapping = {
            "pending": ResourceState.PENDING,
            "running": ResourceState.RUNNING,
            "stopped": ResourceState.STOPPED,
            "terminated": ResourceState.TERMINATED,
            "shutting-down": ResourceState.FAILED,
            "stopping": ResourceState.FAILED,
        }
        return mapping.get(state.lower(), ResourceState.UNKNOWN)

    def _map_rds_state(self, state: str) -> ResourceState:
        mapping = {
            "available": ResourceState.RUNNING,
            "creating": ResourceState.PENDING,
            "deleting": ResourceState.TERMINATED,
            "stopped": ResourceState.STOPPED,
            "stopping": ResourceState.STOPPED,
            "starting": ResourceState.PENDING,
            "failed": ResourceState.FAILED,
        }
        return mapping.get(state.lower(), ResourceState.UNKNOWN)

    def _get_instance_name(self, tags: list[dict]) -> str | None:
        for tag in (tags or []):
            if tag.get("Key") == "Name":
                return tag["Value"]
        return None

    async def discover_resources(self, provider: CloudProvider) -> list[Resource]:
        region = provider.region
        resources: list[Resource] = []

        # EC2 Instances
        try:
            ec2 = self._get_service_client("ec2", region)
            paginator = ec2.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page["Reservations"]:
                    for inst in reservation["Instances"]:
                        if inst["State"]["Name"] == "terminated":
                            continue
                        name = self._get_instance_name(inst.get("Tags")) or inst["InstanceId"]
                        resources.append(Resource(
                            id=uuid4(),
                            provider_id=provider.id,
                            resource_type=ResourceType.COMPUTE_INSTANCE,
                            name=name,
                            state=self._map_instance_state(inst["State"]["Name"]),
                            region=region,
                            arn=inst.get("InstanceId"),
                            metadata=(
                                ("instance_id", inst["InstanceId"]),
                                ("instance_type", inst.get("InstanceType", "")),
                            ),
                        ))
        except Exception as e:
            logger.warning("AWS EC2 discovery failed: %s", e)

        # S3 Buckets
        try:
            s3 = self._get_service_client("s3", region)
            resp = s3.list_buckets()
            for bucket in resp.get("Buckets", []):
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.STORAGE_BUCKET,
                    name=bucket["Name"],
                    state=ResourceState.RUNNING,
                    region=region,
                    arn=f"arn:aws:s3:::{bucket['Name']}",
                ))
        except Exception as e:
            logger.warning("AWS S3 discovery failed: %s", e)

        # RDS Instances
        try:
            rds = self._get_service_client("rds", region)
            paginator = rds.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for db in page["DBInstances"]:
                    resources.append(Resource(
                        id=uuid4(),
                        provider_id=provider.id,
                        resource_type=ResourceType.DATABASE,
                        name=db["DBInstanceIdentifier"],
                        state=self._map_rds_state(db["DBInstanceStatus"]),
                        region=region,
                        arn=db.get("DBInstanceArn"),
                        metadata=(
                            ("db_instance_id", db["DBInstanceIdentifier"]),
                            ("engine", db.get("Engine", "")),
                            ("instance_class", db.get("DBInstanceClass", "")),
                        ),
                    ))
        except Exception as e:
            logger.warning("AWS RDS discovery failed: %s", e)

        # Lambda Functions
        try:
            lam = self._get_service_client("lambda", region)
            paginator = lam.get_paginator("list_functions")
            for page in paginator.paginate():
                for fn in page["Functions"]:
                    resources.append(Resource(
                        id=uuid4(),
                        provider_id=provider.id,
                        resource_type=ResourceType.SERVERLESS_FUNCTION,
                        name=fn["FunctionName"],
                        state=ResourceState.RUNNING,
                        region=region,
                        arn=fn.get("FunctionArn"),
                        metadata=(
                            ("runtime", fn.get("Runtime", "")),
                            ("memory", str(fn.get("MemorySize", ""))),
                        ),
                    ))
        except Exception as e:
            logger.warning("AWS Lambda discovery failed: %s", e)

        # VPCs
        try:
            ec2 = self._get_service_client("ec2", region)
            resp = ec2.describe_vpcs()
            for vpc in resp.get("Vpcs", []):
                name = self._get_instance_name(vpc.get("Tags")) or vpc["VpcId"]
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.NETWORK_VPC,
                    name=name,
                    state=ResourceState.RUNNING,
                    region=region,
                    arn=vpc["VpcId"],
                    metadata=(
                        ("vpc_id", vpc["VpcId"]),
                        ("cidr", vpc.get("CidrBlock", "")),
                    ),
                ))
        except Exception as e:
            logger.warning("AWS VPC discovery failed: %s", e)

        # ELBv2 Load Balancers
        try:
            elbv2 = self._get_service_client("elbv2", region)
            paginator = elbv2.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page["LoadBalancers"]:
                    state_code = lb.get("State", {}).get("Code", "active")
                    lb_state = ResourceState.RUNNING if state_code == "active" else ResourceState.PENDING
                    resources.append(Resource(
                        id=uuid4(),
                        provider_id=provider.id,
                        resource_type=ResourceType.LOAD_BALANCER,
                        name=lb["LoadBalancerName"],
                        state=lb_state,
                        region=region,
                        arn=lb.get("LoadBalancerArn"),
                        metadata=(
                            ("type", lb.get("Type", "")),
                            ("scheme", lb.get("Scheme", "")),
                        ),
                    ))
        except Exception as e:
            logger.warning("AWS ELBv2 discovery failed: %s", e)

        # ElastiCache Clusters
        try:
            ec_client = self._get_service_client("elasticache", region)
            paginator = ec_client.get_paginator("describe_cache_clusters")
            for page in paginator.paginate():
                for cluster in page["CacheClusters"]:
                    cache_state = ResourceState.RUNNING if cluster["CacheClusterStatus"] == "available" else ResourceState.PENDING
                    resources.append(Resource(
                        id=uuid4(),
                        provider_id=provider.id,
                        resource_type=ResourceType.CACHE,
                        name=cluster["CacheClusterId"],
                        state=cache_state,
                        region=region,
                        arn=cluster.get("ARN"),
                        metadata=(
                            ("engine", cluster.get("Engine", "")),
                            ("node_type", cluster.get("CacheNodeType", "")),
                        ),
                    ))
        except Exception as e:
            logger.warning("AWS ElastiCache discovery failed: %s", e)

        # SQS Queues
        try:
            sqs = self._get_service_client("sqs", region)
            resp = sqs.list_queues()
            for url in resp.get("QueueUrls", []):
                name = url.rsplit("/", 1)[-1]
                resources.append(Resource(
                    id=uuid4(),
                    provider_id=provider.id,
                    resource_type=ResourceType.MESSAGE_QUEUE,
                    name=name,
                    state=ResourceState.RUNNING,
                    region=region,
                    arn=url,
                ))
        except Exception as e:
            logger.warning("AWS SQS discovery failed: %s", e)

        logger.info("AWS discovery found %d resources in %s", len(resources), region)
        return resources

    async def create(self, provider: CloudProvider, config: dict) -> Resource:
        ec2 = self._get_client(provider.region)

        instance_type = config.get("instance_type", "t3.micro")
        ami = config.get("ami", "ami-0c55b159cbfafe1f0")

        response = ec2.run_instances(
            InstanceType=instance_type,
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": k, "Value": v}
                        for k, v in (config.get("tags", {})).items()
                    ],
                },
            ],
        )

        instance = response["Instances"][0]

        return Resource(
            id=instance["InstanceId"],
            provider_id=provider.id,
            resource_type=self._map_instance_state(instance["InstanceType"]),
            name=config.get("name", instance["InstanceId"]),
            state=self._map_instance_state(instance["State"]["Name"]),
            region=provider.region,
            arn=instance["InstanceId"],
            tags=config.get("tags", {}),
        )

    async def start(self, resource: Resource) -> bool:
        ec2 = self._get_client(resource.region)
        ec2.start_instances(InstanceIds=[str(resource.id)])
        return True

    async def stop(self, resource: Resource) -> bool:
        ec2 = self._get_client(resource.region)
        ec2.stop_instances(InstanceIds=[str(resource.id)])
        return True

    async def terminate(self, resource: Resource) -> bool:
        ec2 = self._get_client(resource.region)
        ec2.terminate_instances(InstanceIds=[str(resource.id)])
        return True

    async def get_status(self, resource: Resource) -> str:
        ec2 = self._get_client(resource.region)
        response = ec2.describe_instances(InstanceIds=[str(resource.id)])
        if response["Reservations"]:
            instance = response["Reservations"][0]["Instances"][0]
            return instance["State"]["Name"]
        return "unknown"

    async def update_tags(self, resource: Resource, tags: dict) -> bool:
        ec2 = self._get_client(resource.region)
        ec2.create_tags(
            Resources=[str(resource.id)],
            Tags=[{"Key": k, "Value": v} for k, v in tags.items()],
        )
        return True
