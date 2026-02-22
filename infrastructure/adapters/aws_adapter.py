"""
AWS Cloud Provider Adapter

Architectural Intent:
- Real AWS implementation using boto3
- Implements CloudProviderPort interface
- Following Rule 2: Interface-First Development
"""

import boto3
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.entities.cloud_provider import CloudProvider, ProviderStatus
from domain.entities.resource import Resource, ResourceType, ResourceState
from domain.ports.infrastructure_ports import CloudProviderPort, ResourcePort
from domain.value_objects.money import Money


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

    def _get_client(self, region: str):
        if region not in self._clients:
            self._clients[region] = boto3.client(
                "ec2",
                region_name=region,
                aws_access_key_id=self._credentials.get("access_key"),
                aws_secret_access_key=self._credentials.get("secret_key"),
            )
        return self._clients[region]

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

    def _map_resource_type(self, instance_type: str) -> ResourceType:
        if "t3" in instance_type or "t2" in instance_type:
            return ResourceType.COMPUTE_INSTANCE
        elif "rds" in instance_type:
            return ResourceType.DATABASE
        elif "s3" in instance_type:
            return ResourceType.STORAGE_BUCKET
        elif "lambda" in instance_type:
            return ResourceType.SERVERLESS_FUNCTION
        return ResourceType.COMPUTE_INSTANCE

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
