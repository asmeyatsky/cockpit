"""
Domain Tests - Agent Identity & MCP OAuth (PRD 4.5, 4.6)

Architectural Intent:
- Tests agent permission management and MCP OAuth tokens
- Pure domain tests, no mocks needed
"""

import pytest
from uuid import uuid4

from domain.services.agent_identity import (
    AgentIdentityService,
    AgentIdentity,
    AgentPermission,
    MCPOAuthToken,
)


class TestAgentIdentityService:
    def setup_method(self):
        self.service = AgentIdentityService()

    def test_create_identity_with_role(self):
        agent_id = uuid4()
        identity = self.service.create_identity(agent_id, "EPA Agent", role="EPA")
        assert isinstance(identity, AgentIdentity)
        assert AgentPermission.ADMIN in identity.permissions

    def test_create_identity_fia_role(self):
        identity = self.service.create_identity(uuid4(), "FIA", role="FIA")
        assert AgentPermission.READ_COSTS in identity.permissions
        assert AgentPermission.ADMIN not in identity.permissions

    def test_check_access_admin(self):
        agent_id = uuid4()
        self.service.create_identity(agent_id, "EPA", role="EPA")
        assert self.service.check_access(agent_id, AgentPermission.READ_RESOURCES) is True
        assert self.service.check_access(agent_id, AgentPermission.EXECUTE_MIGRATIONS) is True

    def test_check_access_denied(self):
        agent_id = uuid4()
        self.service.create_identity(agent_id, "PMA", role="PMA")
        assert self.service.check_access(agent_id, AgentPermission.EXECUTE_MIGRATIONS) is False

    def test_unknown_agent_denied(self):
        assert self.service.check_access(uuid4(), AgentPermission.READ_RESOURCES) is False

    def test_grant_permission(self):
        agent_id = uuid4()
        self.service.create_identity(agent_id, "Worker")
        self.service.grant_permission(agent_id, AgentPermission.READ_RESOURCES)
        assert self.service.check_access(agent_id, AgentPermission.READ_RESOURCES) is True

    def test_revoke_permission(self):
        agent_id = uuid4()
        self.service.create_identity(agent_id, "FIA", role="FIA")
        self.service.revoke_permission(agent_id, AgentPermission.READ_COSTS)
        assert self.service.check_access(agent_id, AgentPermission.READ_COSTS) is False

    def test_identity_to_dict(self):
        identity = self.service.create_identity(uuid4(), "GA", role="GA")
        d = identity.to_dict()
        assert "permissions" in d
        assert "scopes" in d


class TestMCPOAuth:
    def setup_method(self):
        self.service = AgentIdentityService()

    def test_issue_token(self):
        agent_id = uuid4()
        self.service.create_identity(agent_id, "RSA", role="RSA")
        token = self.service.issue_mcp_token(agent_id)
        assert isinstance(token, MCPOAuthToken)
        assert token.agent_id == agent_id
        assert len(token.scopes) > 0

    def test_validate_token(self):
        agent_id = uuid4()
        self.service.create_identity(agent_id, "FIA", role="FIA")
        token = self.service.issue_mcp_token(agent_id)
        assert self.service.validate_token(token.token_id, "read:costs") is True
        assert self.service.validate_token(token.token_id, "admin") is False

    def test_unknown_token_invalid(self):
        assert self.service.validate_token(uuid4(), "read:resources") is False

    def test_issue_token_unknown_agent(self):
        assert self.service.issue_mcp_token(uuid4()) is None
