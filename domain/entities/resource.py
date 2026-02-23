"""
Infrastructure Resource Domain Entity

Architectural Intent:
- Represents any cloud resource (EC2, VM, S3 bucket, etc.)
- Resource aggregate manages lifecycle state transitions
- Supports all cloud provider resource types

MCP Integration:
- Exposed via infrastructure-resource MCP server
- Tools: create_resource, update_resource, delete_resource, list_resources
- Resources: resource://{resource_id}, resource://list
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4

from domain.exceptions import DomainError


class ResourceType(Enum):
    COMPUTE_INSTANCE = "compute_instance"
    CONTAINER = "container"
    SERVERLESS_FUNCTION = "serverless_function"
    STORAGE_BUCKET = "storage_bucket"
    DATABASE = "database"
    NETWORK_VPC = "network_vpc"
    LOAD_BALANCER = "load_balancer"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    SECRET = "secret"
    CERTIFICATE = "certificate"


class ResourceState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Resource:
    id: UUID
    provider_id: UUID
    resource_type: ResourceType
    name: str
    state: ResourceState
    region: str
    arn: str | None = None
    metadata: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple = field(default_factory=tuple)

    def start(self) -> "Resource":
        if self.state != ResourceState.STOPPED:
            raise DomainError(f"Cannot start resource in state: {self.state}")
        return replace(
            self,
            state=ResourceState.RUNNING,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (ResourceStateChangedEvent(self.id, ResourceState.RUNNING),),
        )

    def stop(self) -> "Resource":
        if self.state != ResourceState.RUNNING:
            raise DomainError(f"Cannot stop resource in state: {self.state}")
        return replace(
            self,
            state=ResourceState.STOPPED,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (ResourceStateChangedEvent(self.id, ResourceState.STOPPED),),
        )

    def terminate(self) -> "Resource":
        if self.state == ResourceState.TERMINATED:
            raise DomainError("Resource already terminated")
        return replace(
            self,
            state=ResourceState.TERMINATED,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (ResourceStateChangedEvent(self.id, ResourceState.TERMINATED),),
        )

    def fail(self, error: str) -> "Resource":
        return replace(
            self,
            state=ResourceState.FAILED,
            updated_at=datetime.now(UTC),
            metadata={**self.metadata, "error": error},
            domain_events=self.domain_events
            + (ResourceStateChangedEvent(self.id, ResourceState.FAILED, error),),
        )

    def add_tag(self, key: str, value: str) -> "Resource":
        return replace(
            self,
            tags={**self.tags, key: value},
            updated_at=datetime.now(UTC),
        )

    def remove_tag(self, key: str) -> "Resource":
        new_tags = {k: v for k, v in self.tags.items() if k != key}
        return replace(
            self,
            tags=new_tags,
            updated_at=datetime.now(UTC),
        )


@dataclass(frozen=True)
class ResourceStateChangedEvent:
    resource_id: UUID
    new_state: ResourceState
    error: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = ["Resource", "ResourceType", "ResourceState", "ResourceStateChangedEvent"]
