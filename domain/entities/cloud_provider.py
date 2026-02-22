"""
Cloud Provider Domain Entity

Architectural Intent:
- Represents a cloud provider (AWS, Azure, GCP, OCI) in the system
- Provider aggregate is the consistency boundary for provider operations
- All state changes go through domain methods to enforce invariants

MCP Integration:
- Exposed via infrastructure-provider MCP server
- Resources: provider://{provider_id} for read access

Key Design Decisions:
1. Providers are identified by type enum - no string-based provider detection
2. Connection status is managed through domain events
3. Credentials are value objects - never stored directly on entity
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, UTC
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4


class CloudProviderType(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    OCI = "oci"


class ProviderStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(frozen=True)
class CloudProvider:
    id: UUID
    provider_type: CloudProviderType
    name: str
    status: ProviderStatus
    region: str
    account_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    domain_events: tuple = field(default_factory=tuple)

    def connect(self) -> "CloudProvider":
        if self.status == ProviderStatus.CONNECTED:
            raise DomainError("Provider already connected")
        return replace(
            self,
            status=ProviderStatus.CONNECTED,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (ProviderConnectedEvent(self.id, self.provider_type),),
        )

    def disconnect(self) -> "CloudProvider":
        if self.status == ProviderStatus.DISCONNECTED:
            raise DomainError("Provider already disconnected")
        return replace(
            self,
            status=ProviderStatus.DISCONNECTED,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (ProviderDisconnectedEvent(self.id, self.provider_type),),
        )

    def set_error(self, error_message: str) -> "CloudProvider":
        return replace(
            self,
            status=ProviderStatus.ERROR,
            updated_at=datetime.now(UTC),
            domain_events=self.domain_events
            + (ProviderErrorEvent(self.id, self.provider_type, error_message),),
        )


@dataclass(frozen=True)
class ProviderConnectedEvent:
    provider_id: UUID
    provider_type: CloudProviderType
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ProviderDisconnectedEvent:
    provider_id: UUID
    provider_type: CloudProviderType
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ProviderErrorEvent:
    provider_id: UUID
    provider_type: CloudProviderType
    error_message: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DomainError(Exception):
    pass
