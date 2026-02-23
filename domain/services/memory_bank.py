"""
Memory Bank for Cross-Session Context (PRD 4.10)

Architectural Intent:
- Provides persistent memory across agent sessions
- Stores decision records, conventions, and glossary
- Following AI-Native Context Pattern 3 from skill2026.md

MCP Integration:
- Exposed via MCP Resources for agent context retrieval
- Resources: memory://decisions, memory://conventions, memory://glossary
- Tools: store_decision, store_convention, recall_context

Parallelization Strategy:
- Read operations can be fully parallelized
- Write operations use append-only pattern for safety
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class MemoryEntry:
    """Single memory entry in the memory bank."""
    id: UUID
    category: str  # "decision", "convention", "glossary", "context"
    key: str
    content: str
    agent_id: Optional[UUID] = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "category": self.category,
            "key": self.key,
            "content": self.content,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
        }


class MemoryBank:
    """
    In-memory implementation of cross-session memory bank.
    Stores decisions, conventions, glossary entries, and contextual data.
    """

    def __init__(self):
        self._entries: dict[UUID, MemoryEntry] = {}

    def store(
        self,
        category: str,
        key: str,
        content: str,
        agent_id: Optional[UUID] = None,
        tags: tuple[str, ...] = (),
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=uuid4(),
            category=category,
            key=key,
            content=content,
            agent_id=agent_id,
            tags=tags,
        )
        self._entries[entry.id] = entry
        return entry

    def recall(
        self,
        category: Optional[str] = None,
        key: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        tags: Optional[tuple[str, ...]] = None,
    ) -> list[MemoryEntry]:
        results = []
        for entry in self._entries.values():
            if entry.is_expired():
                continue
            if category and entry.category != category:
                continue
            if key and key.lower() not in entry.key.lower():
                continue
            if agent_id and entry.agent_id != agent_id:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            results.append(entry)
        return sorted(results, key=lambda e: e.created_at, reverse=True)

    def recall_decisions(self) -> list[MemoryEntry]:
        return self.recall(category="decision")

    def recall_conventions(self) -> list[MemoryEntry]:
        return self.recall(category="convention")

    def recall_glossary(self) -> list[MemoryEntry]:
        return self.recall(category="glossary")

    def get_context_for_agent(self, agent_id: UUID, max_entries: int = 20) -> list[MemoryEntry]:
        """Get relevant context for a specific agent."""
        agent_specific = self.recall(agent_id=agent_id)
        general = self.recall(category="convention")
        combined = agent_specific + [e for e in general if e not in agent_specific]
        return combined[:max_entries]

    def delete(self, entry_id: UUID) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def clear(self) -> None:
        self._entries.clear()

    @property
    def size(self) -> int:
        return len(self._entries)
