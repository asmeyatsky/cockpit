"""
Domain Tests - Agent Entity

Architectural Intent:
- Domain model tests - no mocks needed, pure logic
- Tests verify agent lifecycle state transitions
"""

import pytest
from uuid import uuid4

from domain.entities.agent import (
    Agent,
    AgentCapability,
    AgentConfig,
    AIProvider,
    AgentStatus,
    AgentActivatedEvent,
    AgentDeactivatedEvent,
    AgentErrorEvent,
)


class TestAgent:
    def test_create_agent(self):
        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.INACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
                max_tokens=4096,
                temperature=0.7,
                system_prompt="You are helpful",
            ),
            capabilities=(),
        )

        assert agent.name == "test-agent"
        assert agent.status == AgentStatus.INACTIVE
        assert agent.config.provider == AIProvider.CLAUDE
        assert agent.config.model == "claude-3-5-sonnet"

    def test_activate_agent(self):
        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.INACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
            ),
            capabilities=(),
        )

        activated_agent = agent.activate()

        assert activated_agent.status == AgentStatus.ACTIVE
        assert agent.status == AgentStatus.INACTIVE
        assert len(activated_agent.domain_events) == 1
        assert isinstance(activated_agent.domain_events[0], AgentActivatedEvent)

    def test_activate_already_active_agent(self):
        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.ACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
            ),
            capabilities=(),
        )

        with pytest.raises(Exception):
            agent.activate()

    def test_deactivate_agent(self):
        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.ACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
            ),
            capabilities=(),
        )

        deactivated_agent = agent.deactivate()

        assert deactivated_agent.status == AgentStatus.INACTIVE
        assert agent.status == AgentStatus.ACTIVE

    def test_set_error(self):
        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.ACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
            ),
            capabilities=(),
        )

        error_agent = agent.set_error("API rate limit exceeded")

        assert error_agent.status == AgentStatus.ERROR
        assert len(error_agent.domain_events) == 1
        assert isinstance(error_agent.domain_events[0], AgentErrorEvent)
        assert error_agent.domain_events[0].error_message == "API rate limit exceeded"

    def test_add_capability(self):
        capability = AgentCapability(
            name="web_scraper",
            description="Can scrape websites",
            mcp_servers=("web-service",),
        )

        agent = Agent(
            id=uuid4(),
            name="test-agent",
            description="A test agent",
            status=AgentStatus.INACTIVE,
            config=AgentConfig(
                provider=AIProvider.CLAUDE,
                model="claude-3-5-sonnet",
            ),
            capabilities=(),
        )

        updated_agent = agent.add_capability(capability)

        assert len(updated_agent.capabilities) == 1
        assert updated_agent.capabilities[0].name == "web_scraper"
        assert agent.capabilities == ()


class TestAgentConfig:
    def test_create_config(self):
        config = AgentConfig(
            provider=AIProvider.OPENAI,
            model="gpt-4",
            max_tokens=8192,
            temperature=0.5,
            system_prompt="You are a coding assistant",
        )

        assert config.provider == AIProvider.OPENAI
        assert config.model == "gpt-4"
        assert config.max_tokens == 8192
        assert config.temperature == 0.5

    def test_default_values(self):
        config = AgentConfig(
            provider=AIProvider.GEMINI,
            model="gemini-pro",
        )

        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.system_prompt == ""


class TestAgentCapability:
    def test_create_capability(self):
        capability = AgentCapability(
            name="image_generator",
            description="Generates images from text",
            mcp_servers=("image-service", "storage-service"),
        )

        assert capability.name == "image_generator"
        assert capability.description == "Generates images from text"
        assert len(capability.mcp_servers) == 2

    def test_capability_immutability(self):
        capability = AgentCapability(
            name="test",
            description="Test",
            mcp_servers=("server1",),
        )

        assert capability.mcp_servers == ("server1",)
