"""
Domain Tests - HMAS Agent Hierarchy (PRD 4.1, 4.2, 4.3)

Architectural Intent:
- Tests HMAS agent creation, hierarchy, and A2A Agent Cards
- Pure domain tests, no mocks needed
"""

import pytest
from uuid import uuid4

from domain.entities.hmas_agents import (
    HMASAgent, HMASLevel, HMASRole, AgentCard,
    ROLE_DESCRIPTIONS, ROLE_LEVELS,
    AgentChildAddedEvent, TaskDelegatedEvent,
    create_default_hierarchy,
)
from domain.exceptions import DomainError


class TestHMASAgent:
    def test_create_epa_agent(self):
        agent = HMASAgent(
            id=uuid4(),
            name="EPA",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description="Executive Planning Agent",
        )
        assert agent.role == HMASRole.EPA
        assert agent.level == HMASLevel.L3_EXECUTIVE
        assert agent.status == "active"

    def test_create_l2_agent(self):
        agent = HMASAgent(
            id=uuid4(),
            name="RSA Agent",
            role=HMASRole.RSA,
            level=HMASLevel.L2_SPECIALIST,
            description="Refactoring Strategy",
        )
        assert agent.level == HMASLevel.L2_SPECIALIST

    def test_invalid_role_level_raises_error(self):
        with pytest.raises(DomainError, match="must be level"):
            HMASAgent(
                id=uuid4(),
                name="Bad",
                role=HMASRole.EPA,
                level=HMASLevel.L1_WORKER,
                description="Wrong level",
            )

    def test_add_child(self):
        parent_id = uuid4()
        child_id = uuid4()
        agent = HMASAgent(
            id=parent_id,
            name="EPA",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description="EPA",
        )
        updated = agent.add_child(child_id)
        assert child_id in updated.children_ids
        assert len(updated.domain_events) == 1
        assert isinstance(updated.domain_events[0], AgentChildAddedEvent)

    def test_add_duplicate_child_raises(self):
        child_id = uuid4()
        agent = HMASAgent(
            id=uuid4(),
            name="EPA",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description="EPA",
            children_ids=(child_id,),
        )
        with pytest.raises(DomainError, match="already exists"):
            agent.add_child(child_id)

    def test_l1_worker_cannot_have_children(self):
        agent = HMASAgent(
            id=uuid4(),
            name="Worker",
            role=HMASRole.WORKER,
            level=HMASLevel.L1_WORKER,
            description="Worker",
        )
        with pytest.raises(DomainError, match="cannot have children"):
            agent.add_child(uuid4())

    def test_remove_child(self):
        child_id = uuid4()
        agent = HMASAgent(
            id=uuid4(),
            name="EPA",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description="EPA",
            children_ids=(child_id,),
        )
        updated = agent.remove_child(child_id)
        assert child_id not in updated.children_ids

    def test_delegate_task(self):
        child_id = uuid4()
        agent = HMASAgent(
            id=uuid4(),
            name="EPA",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description="EPA",
            children_ids=(child_id,),
        )
        updated = agent.delegate_task("analyze costs", child_id)
        assert len(updated.domain_events) == 1
        assert isinstance(updated.domain_events[0], TaskDelegatedEvent)

    def test_delegate_to_non_child_raises(self):
        agent = HMASAgent(
            id=uuid4(),
            name="EPA",
            role=HMASRole.EPA,
            level=HMASLevel.L3_EXECUTIVE,
            description="EPA",
        )
        with pytest.raises(DomainError, match="non-child"):
            agent.delegate_task("task", uuid4())


class TestAgentCard:
    def test_get_agent_card(self):
        agent = HMASAgent(
            id=uuid4(),
            name="FIA Agent",
            role=HMASRole.FIA,
            level=HMASLevel.L2_SPECIALIST,
            description="Financial Insight",
        )
        card = agent.get_agent_card()
        assert isinstance(card, AgentCard)
        assert card.role == HMASRole.FIA
        assert "a2a" in card.supported_protocols

    def test_agent_card_to_dict(self):
        card = AgentCard(
            agent_id=uuid4(),
            name="Test",
            role=HMASRole.RSA,
            level=HMASLevel.L2_SPECIALIST,
            description="Test agent",
        )
        d = card.to_dict()
        assert d["role"] == "RSA"
        assert d["level"] == "L2"


class TestDefaultHierarchy:
    def test_create_default_hierarchy(self):
        agents = create_default_hierarchy()
        assert len(agents) == 7  # 1 EPA + 6 L2

        epa = agents[0]
        assert epa.role == HMASRole.EPA
        assert len(epa.children_ids) == 6

        l2_roles = {a.role for a in agents[1:]}
        assert HMASRole.RSA in l2_roles
        assert HMASRole.FIA in l2_roles
        assert HMASRole.GA in l2_roles
        assert HMASRole.MVA in l2_roles
        assert HMASRole.DOA in l2_roles
        assert HMASRole.PMA in l2_roles

    def test_all_l2_have_parent(self):
        agents = create_default_hierarchy()
        epa_id = agents[0].id
        for agent in agents[1:]:
            assert agent.parent_id == epa_id


class TestRoleDescriptions:
    def test_all_roles_have_descriptions(self):
        for role in HMASRole:
            assert role in ROLE_DESCRIPTIONS

    def test_all_roles_have_levels(self):
        for role in HMASRole:
            assert role in ROLE_LEVELS
