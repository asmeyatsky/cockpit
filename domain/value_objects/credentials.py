"""
Cloud Credentials Value Object

Architectural Intent:
- Immutable value object for secure credential handling
- Credentials are never logged or exposed
- Supports various authentication methods per provider
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Credentials:
    auth_type: Literal["api_key", "oauth", "service_account", "iam_role"]
    access_key: str | None = None
    secret_key: str | None = None
    token: str | None = None
    refresh_token: str | None = None
    project_id: str | None = None
    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    def is_valid(self) -> bool:
        if self.auth_type == "api_key":
            return bool(self.access_key and self.secret_key)
        elif self.auth_type == "oauth":
            return bool(self.access_key and self.refresh_token)
        elif self.auth_type == "service_account":
            return bool(self.project_id)
        elif self.auth_type == "iam_role":
            return bool(self.access_key)
        return False

    def __repr__(self) -> str:
        return f"Credentials(auth_type={self.auth_type!r}, **REDACTED**)"

    def __str__(self) -> str:
        return self.__repr__()
