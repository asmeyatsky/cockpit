"""
Domain Exceptions

Shared domain-level exceptions used across all entities and services.
"""


class DomainError(Exception):
    """Base exception for domain rule violations."""
    pass
