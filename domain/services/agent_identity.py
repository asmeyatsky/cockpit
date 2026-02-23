"""
Agent Identity & IAM (PRD 4.5) + MCP OAuth 2.1 (PRD 4.6)

Architectural Intent:
- Per-agent permissions and identity management
- Defines what resources and actions each agent can access
- MCP OAuth 2.1 authorization for MCP server access

MCP Integration:
- Resources: identity://{agent_id}/permissions
- Tools: grant_permission, revoke_permission, check_access

Parallelization Strategy:
- Permission checks are stateless and can run concurrently
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional

from domain.exceptions import DomainError


class AgentPermission(Enum):
    """Permissions that can be granted to agents."""
    READ_RESOURCES = "read:resources"
    WRITE_RESOURCES = "write:resources"
    READ_PROVIDERS = "read:providers"
    WRITE_PROVIDERS = "write:providers"
    READ_COSTS = "read:costs"
    EXECUTE_MIGRATIONS = "execute:migrations"
    MANAGE_AGENTS = "manage:agents"
    READ_THREATS = "read:threats"
    MANAGE_THREATS = "manage:threats"
    READ_METRICS = "read:metrics"
    ADMIN = "admin"


@dataclass(frozen=True)
class AgentIdentity:
    """Identity record for an HMAS agent with permissions."""
    agent_id: UUID
    agent_name: str
    permissions: frozenset[AgentPermission] = field(default_factory=frozenset)
    scopes: tuple[str, ...] = field(default_factory=tuple)  # MCP OAuth scopes
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def has_permission(self, permission: AgentPermission) -> bool:
        if AgentPermission.ADMIN in self.permissions:
            return True
        return permission in self.permissions

    def grant(self, permission: AgentPermission) -> "AgentIdentity":
        from dataclasses import replace
        return replace(
            self,
            permissions=self.permissions | {permission},
        )

    def revoke(self, permission: AgentPermission) -> "AgentIdentity":
        from dataclasses import replace
        return replace(
            self,
            permissions=self.permissions - {permission},
        )

    def to_dict(self) -> dict:
        return {
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "permissions": [p.value for p in self.permissions],
            "scopes": list(self.scopes),
        }


@dataclass(frozen=True)
class MCPOAuthToken:
    """MCP OAuth 2.1 token for agent-to-server authorization (PRD 4.6)."""
    token_id: UUID
    agent_id: UUID
    scopes: tuple[str, ...]
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_in: int = 3600  # seconds

    @property
    def is_expired(self) -> bool:
        from datetime import timedelta
        return datetime.now(UTC) > self.issued_at + timedelta(seconds=self.expires_in)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "*" in self.scopes


class AgentIdentityService:
    """Manages agent identities and permissions."""

    # Default permissions per HMAS role
    ROLE_PERMISSIONS = {
        "EPA": frozenset({AgentPermission.ADMIN}),
        "RSA": frozenset({AgentPermission.READ_RESOURCES, AgentPermission.READ_PROVIDERS}),
        "FIA": frozenset({AgentPermission.READ_COSTS, AgentPermission.READ_RESOURCES}),
        "GA": frozenset({AgentPermission.READ_THREATS, AgentPermission.MANAGE_THREATS, AgentPermission.READ_RESOURCES}),
        "MVA": frozenset({AgentPermission.READ_RESOURCES, AgentPermission.EXECUTE_MIGRATIONS}),
        "DOA": frozenset({AgentPermission.READ_RESOURCES, AgentPermission.WRITE_RESOURCES, AgentPermission.READ_PROVIDERS}),
        "PMA": frozenset({AgentPermission.READ_METRICS, AgentPermission.READ_RESOURCES}),
    }

    def __init__(self):
        self._identities: dict[UUID, AgentIdentity] = {}
        self._tokens: dict[UUID, MCPOAuthToken] = {}

    def create_identity(self, agent_id: UUID, agent_name: str, role: str = "") -> AgentIdentity:
        permissions = self.ROLE_PERMISSIONS.get(role, frozenset())
        identity = AgentIdentity(
            agent_id=agent_id,
            agent_name=agent_name,
            permissions=permissions,
            scopes=tuple(p.value for p in permissions),
        )
        self._identities[agent_id] = identity
        return identity

    def check_access(self, agent_id: UUID, permission: AgentPermission) -> bool:
        identity = self._identities.get(agent_id)
        if not identity:
            return False
        return identity.has_permission(permission)

    def grant_permission(self, agent_id: UUID, permission: AgentPermission) -> Optional[AgentIdentity]:
        identity = self._identities.get(agent_id)
        if not identity:
            return None
        identity = identity.grant(permission)
        self._identities[agent_id] = identity
        return identity

    def revoke_permission(self, agent_id: UUID, permission: AgentPermission) -> Optional[AgentIdentity]:
        identity = self._identities.get(agent_id)
        if not identity:
            return None
        identity = identity.revoke(permission)
        self._identities[agent_id] = identity
        return identity

    def issue_mcp_token(self, agent_id: UUID) -> Optional[MCPOAuthToken]:
        """Issue MCP OAuth 2.1 token for agent (PRD 4.6)."""
        identity = self._identities.get(agent_id)
        if not identity:
            return None
        token = MCPOAuthToken(
            token_id=uuid4(),
            agent_id=agent_id,
            scopes=identity.scopes,
        )
        self._tokens[token.token_id] = token
        return token

    def validate_token(self, token_id: UUID, required_scope: str) -> bool:
        """Validate MCP OAuth token and check scope."""
        token = self._tokens.get(token_id)
        if not token or token.is_expired:
            return False
        return token.has_scope(required_scope)

    def get_identity(self, agent_id: UUID) -> Optional[AgentIdentity]:
        return self._identities.get(agent_id)
