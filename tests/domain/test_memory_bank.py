"""
Domain Tests - Memory Bank (PRD 4.10)

Architectural Intent:
- Tests cross-session memory storage and retrieval
- Pure domain tests, no mocks needed
"""

import pytest
from uuid import uuid4

from domain.services.memory_bank import MemoryBank, MemoryEntry


class TestMemoryBank:
    def setup_method(self):
        self.bank = MemoryBank()

    def test_store_and_recall(self):
        entry = self.bank.store("decision", "auth-method", "Use JWT for API auth")
        assert isinstance(entry, MemoryEntry)
        results = self.bank.recall(category="decision")
        assert len(results) == 1
        assert results[0].content == "Use JWT for API auth"

    def test_recall_by_key(self):
        self.bank.store("convention", "naming", "Use snake_case for Python")
        self.bank.store("convention", "testing", "Use pytest")
        results = self.bank.recall(key="naming")
        assert len(results) == 1

    def test_recall_by_agent(self):
        agent_id = uuid4()
        self.bank.store("context", "task", "Deploy to prod", agent_id=agent_id)
        self.bank.store("context", "task", "Run tests", agent_id=uuid4())
        results = self.bank.recall(agent_id=agent_id)
        assert len(results) == 1

    def test_recall_by_tags(self):
        self.bank.store("decision", "db", "Use PostgreSQL", tags=("database", "infra"))
        self.bank.store("decision", "cache", "Use Redis", tags=("cache",))
        results = self.bank.recall(tags=("database",))
        assert len(results) == 1

    def test_recall_decisions(self):
        self.bank.store("decision", "k1", "v1")
        self.bank.store("convention", "k2", "v2")
        assert len(self.bank.recall_decisions()) == 1
        assert len(self.bank.recall_conventions()) == 1

    def test_get_context_for_agent(self):
        agent_id = uuid4()
        self.bank.store("context", "task", "specific", agent_id=agent_id)
        self.bank.store("convention", "general", "always test")
        entries = self.bank.get_context_for_agent(agent_id)
        assert len(entries) == 2

    def test_delete(self):
        entry = self.bank.store("decision", "k", "v")
        assert self.bank.size == 1
        self.bank.delete(entry.id)
        assert self.bank.size == 0

    def test_clear(self):
        self.bank.store("decision", "k1", "v1")
        self.bank.store("decision", "k2", "v2")
        self.bank.clear()
        assert self.bank.size == 0

    def test_entry_to_dict(self):
        entry = self.bank.store("decision", "auth", "JWT", tags=("security",))
        d = entry.to_dict()
        assert d["category"] == "decision"
        assert d["key"] == "auth"
        assert "security" in d["tags"]
