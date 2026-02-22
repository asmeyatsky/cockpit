"""
Domain Tests - Resource Entity

Architectural Intent:
- Domain model tests - no mocks needed, pure logic
- Tests verify resource lifecycle state transitions
"""

import pytest
from uuid import uuid4

from domain.entities.resource import (
    Resource,
    ResourceType,
    ResourceState,
    ResourceStateChangedEvent,
)


class TestResource:
    def test_create_resource(self):
        provider_id = uuid4()
        resource = Resource(
            id=uuid4(),
            provider_id=provider_id,
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.PENDING,
            region="us-east-1",
        )

        assert resource.name == "web-server"
        assert resource.state == ResourceState.PENDING
        assert resource.resource_type == ResourceType.COMPUTE_INSTANCE

    def test_start_resource(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.STOPPED,
            region="us-east-1",
        )

        started_resource = resource.start()

        assert started_resource.state == ResourceState.RUNNING
        assert resource.state == ResourceState.STOPPED
        assert len(started_resource.domain_events) == 1
        assert started_resource.domain_events[0].new_state == ResourceState.RUNNING

    def test_start_already_running_resource(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        with pytest.raises(Exception):
            resource.start()

    def test_stop_resource(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        stopped_resource = resource.stop()

        assert stopped_resource.state == ResourceState.STOPPED
        assert resource.state == ResourceState.RUNNING

    def test_terminate_resource(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        terminated_resource = resource.terminate()

        assert terminated_resource.state == ResourceState.TERMINATED

    def test_fail_resource(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        failed_resource = resource.fail("Out of memory")

        assert failed_resource.state == ResourceState.FAILED
        assert failed_resource.metadata["error"] == "Out of memory"

    def test_add_tag(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
            tags={},
        )

        tagged_resource = resource.add_tag("environment", "production")

        assert tagged_resource.tags["environment"] == "production"
        assert resource.tags == {}

    def test_remove_tag(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
            tags={"environment": "production", "team": "platform"},
        )

        untagged_resource = resource.remove_tag("environment")

        assert "environment" not in untagged_resource.tags
        assert untagged_resource.tags["team"] == "platform"

    def test_resource_immutability(self):
        resource = Resource(
            id=uuid4(),
            provider_id=uuid4(),
            resource_type=ResourceType.COMPUTE_INSTANCE,
            name="web-server",
            state=ResourceState.RUNNING,
            region="us-east-1",
        )

        original_state = resource.state
        resource.add_tag("test", "value")

        assert resource.state == original_state
