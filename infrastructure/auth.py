"""
Authentication & Authorization

Architectural Intent:
- JWT-based authentication
- Role-based access control (RBAC)
- API key authentication for service accounts
- bcrypt password hashing for security
"""

import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, UTC
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel

try:
    import bcrypt

    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

import jwt


class Role(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(Enum):
    PROVIDER_CREATE = "provider:create"
    PROVIDER_READ = "provider:read"
    PROVIDER_UPDATE = "provider:update"
    PROVIDER_DELETE = "provider:delete"
    RESOURCE_CREATE = "resource:create"
    RESOURCE_READ = "resource:read"
    RESOURCE_UPDATE = "resource:update"
    RESOURCE_DELETE = "resource:delete"
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    COST_READ = "cost:read"
    ADMIN = "admin"


ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],
    Role.OPERATOR: [
        Permission.PROVIDER_CREATE,
        Permission.PROVIDER_READ,
        Permission.PROVIDER_UPDATE,
        Permission.RESOURCE_CREATE,
        Permission.RESOURCE_READ,
        Permission.RESOURCE_UPDATE,
        Permission.RESOURCE_DELETE,
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.COST_READ,
    ],
    Role.VIEWER: [
        Permission.PROVIDER_READ,
        Permission.RESOURCE_READ,
        Permission.AGENT_READ,
        Permission.COST_READ,
    ],
}


@dataclass
class User:
    id: str
    username: str
    email: str
    role: Role
    hashed_password: str
    api_key: Optional[str] = None
    created_at: datetime = None


@dataclass
class TokenData:
    user_id: str
    username: str
    role: Role
    exp: datetime


class AuthService:
    def __init__(self, secret_key: Optional[str] = None):
        self._secret_key = secret_key or os.environ.get("COCKPIT_SECRET_KEY")
        if not self._secret_key:
            self._secret_key = secrets.token_urlsafe(32)
            import logging
            logging.getLogger(__name__).warning(
                "COCKPIT_SECRET_KEY not set — using ephemeral key. "
                "Tokens will not survive restarts. Set COCKPIT_SECRET_KEY in production."
            )
        self._algorithm = "HS256"
        self._users: dict[str, User] = {}

    def create_user(
        self, username: str, email: str, password: str, role: Role = Role.VIEWER
    ) -> User:
        user_id = secrets.token_urlsafe(16)
        hashed = self._hash_password(password)

        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            hashed_password=hashed,
        )
        self._users[user_id] = user
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username and self._verify_password(
                password, user.hashed_password
            ):
                return user
        return None

    def create_token(
        self, user: User, expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(hours=24)

        to_encode = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": expire,
        }
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> Optional[TokenData]:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return TokenData(
                user_id=payload["user_id"],
                username=payload["username"],
                role=Role(payload["role"]),
                exp=datetime.fromtimestamp(payload["exp"], UTC),
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def create_api_key(self, user: User) -> str:
        api_key = f"ck_{secrets.token_urlsafe(32)}"
        user.api_key = api_key
        return api_key

    def verify_api_key(self, api_key: str) -> Optional[User]:
        if not api_key.startswith("ck_"):
            return None
        for user in self._users.values():
            if user.api_key and hmac.compare_digest(user.api_key, api_key):
                return user
        return None

    def _hash_password(self, password: str) -> str:
        if _HAS_BCRYPT:
            return bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
        # Fallback: PBKDF2 with SHA-256 (stdlib, no extra dependency)
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 600_000)
        return f"pbkdf2:{salt}:{dk.hex()}"

    def _verify_password(self, password: str, hashed: str) -> bool:
        if _HAS_BCRYPT and hashed.startswith("$2"):
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed.encode("utf-8")
            )
        if hashed.startswith("pbkdf2:"):
            _, salt, stored_hash = hashed.split(":", 2)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), 600_000)
            return hmac.compare_digest(dk.hex(), stored_hash)
        # Legacy SHA-256 fallback for existing hashes
        return hmac.compare_digest(
            hashlib.sha256(password.encode()).hexdigest(), hashed
        )


class AuthorizationService:
    def __init__(self, auth_service: AuthService):
        self._auth = auth_service

    def check_permission(self, user: User, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(user.role, [])

    def require_permission(self, user: User, permission: Permission):
        if not self.check_permission(user, permission):
            raise PermissionError(f"Missing required permission: {permission.value}")


_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def get_authorization_service() -> AuthorizationService:
    return AuthorizationService(get_auth_service())
