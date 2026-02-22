"""
Domain Tests - Credentials Value Object

Architectural Intent:
- Domain model tests - no mocks needed, pure logic
- Tests verify credentials validation
"""

import pytest

from domain.value_objects.credentials import Credentials


class TestCredentials:
    def test_create_api_key_credentials(self):
        creds = Credentials(
            auth_type="api_key",
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        assert creds.auth_type == "api_key"
        assert creds.access_key == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    def test_create_oauth_credentials(self):
        creds = Credentials(
            auth_type="oauth",
            access_key="ya29.a0AfH6S...",
            refresh_token="1//0gK-Z...",
        )

        assert creds.auth_type == "oauth"
        assert creds.access_key == "ya29.a0AfH6S..."

    def test_create_service_account_credentials(self):
        creds = Credentials(
            auth_type="service_account",
            project_id="my-project-123",
        )

        assert creds.auth_type == "service_account"
        assert creds.project_id == "my-project-123"

    def test_is_valid_api_key(self):
        creds = Credentials(
            auth_type="api_key",
            access_key="key",
            secret_key="secret",
        )

        assert creds.is_valid() is True

    def test_is_valid_api_key_missing_secret(self):
        creds = Credentials(
            auth_type="api_key",
            access_key="key",
        )

        assert creds.is_valid() is False

    def test_is_valid_oauth(self):
        creds = Credentials(
            auth_type="oauth",
            access_key="token",
            refresh_token="refresh",
        )

        assert creds.is_valid() is True

    def test_is_valid_oauth_missing_refresh(self):
        creds = Credentials(
            auth_type="oauth",
            access_key="token",
        )

        assert creds.is_valid() is False

    def test_is_valid_service_account(self):
        creds = Credentials(
            auth_type="service_account",
            project_id="my-project",
        )

        assert creds.is_valid() is True

    def test_is_valid_iam_role(self):
        creds = Credentials(
            auth_type="iam_role",
            access_key="role-arn:aws:iam::123456789:role/MyRole",
        )

        assert creds.is_valid() is True

    def test_is_valid_unknown_type(self):
        creds = Credentials(auth_type="unknown")

        assert creds.is_valid() is False


class TestCredentialsImmutability:
    def test_credentials_are_immutable(self):
        creds = Credentials(
            auth_type="api_key",
            access_key="key",
            secret_key="secret",
        )

        original_access = creds.access_key

        assert creds.access_key == original_access
