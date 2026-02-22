"""
Domain Tests - Cloud Provider Entity

Architectural Intent:
- Following Rule 4: Mandatory Testing Coverage
- Domain model tests - no mocks needed, pure logic
- Tests verify domain behavior and invariants
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from domain.entities.cloud_provider import (
    CloudProvider,
    CloudProviderType,
    ProviderStatus,
    ProviderConnectedEvent,
    ProviderDisconnectedEvent,
    ProviderErrorEvent,
)


class TestCloudProvider:
    def test_create_provider(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
            account_id="123456789",
        )

        assert provider.provider_type == CloudProviderType.AWS
        assert provider.status == ProviderStatus.DISCONNECTED
        assert provider.region == "us-east-1"
        assert provider.account_id == "123456789"

    def test_connect_provider(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
        )

        connected_provider = provider.connect()

        assert connected_provider.status == ProviderStatus.CONNECTED
        assert provider.status == ProviderStatus.DISCONNECTED
        assert len(connected_provider.domain_events) == 1
        assert isinstance(connected_provider.domain_events[0], ProviderConnectedEvent)

    def test_connect_already_connected_provider(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )

        with pytest.raises(Exception):
            provider.connect()

    def test_disconnect_provider(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )

        disconnected_provider = provider.disconnect()

        assert disconnected_provider.status == ProviderStatus.DISCONNECTED
        assert provider.status == ProviderStatus.CONNECTED
        assert len(disconnected_provider.domain_events) == 1
        assert isinstance(
            disconnected_provider.domain_events[0], ProviderDisconnectedEvent
        )

    def test_set_error(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.CONNECTED,
            region="us-east-1",
        )

        error_provider = provider.set_error("Connection timeout")

        assert error_provider.status == ProviderStatus.ERROR
        assert len(error_provider.domain_events) == 1
        assert isinstance(error_provider.domain_events[0], ProviderErrorEvent)
        assert error_provider.domain_events[0].error_message == "Connection timeout"

    def test_provider_immutability(self):
        provider = CloudProvider(
            id=uuid4(),
            provider_type=CloudProviderType.AWS,
            name="aws-prod",
            status=ProviderStatus.DISCONNECTED,
            region="us-east-1",
        )

        provider.connect()

        assert provider.status == ProviderStatus.DISCONNECTED
