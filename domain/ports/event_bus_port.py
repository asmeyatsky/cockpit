"""
Event Bus Port

Architectural Intent:
- Defines port interface for domain event publishing
- Enables event-driven communication across bounded contexts
- Supports both synchronous and asynchronous handlers
"""

from abc import ABC, abstractmethod
from typing import Protocol, Callable, Any
from dataclasses import dataclass


@dataclass
class DomainEvent:
    occurred_at: Any


class EventBusPort(Protocol):
    async def publish(self, events: list[DomainEvent]) -> None: ...
    async def subscribe(self, event_type: type, handler: Callable) -> None: ...
    async def unsubscribe(self, event_type: type, handler: Callable) -> None: ...
