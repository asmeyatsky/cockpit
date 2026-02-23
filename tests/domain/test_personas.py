"""
Domain Tests - Persona-Driven Views (PRD 4.9)

Architectural Intent:
- Tests persona configurations and dashboard widgets
- Pure domain tests, no mocks needed
"""

import pytest

from domain.services.personas import (
    PersonaService,
    PersonaType,
    PersonaConfig,
    PERSONA_CONFIGS,
)


class TestPersonaService:
    def setup_method(self):
        self.service = PersonaService()

    def test_get_sales_config(self):
        config = self.service.get_config(PersonaType.SALES)
        assert isinstance(config, PersonaConfig)
        assert config.persona == PersonaType.SALES
        assert len(config.widgets) > 0
        assert "create_proposal" in config.quick_actions

    def test_get_presales_config(self):
        config = self.service.get_config(PersonaType.PRESALES)
        assert config.persona == PersonaType.PRESALES
        assert any(w.id == "readiness" for w in config.widgets)

    def test_get_delivery_config(self):
        config = self.service.get_config(PersonaType.DELIVERY)
        assert config.persona == PersonaType.DELIVERY
        assert "deploy_resources" in config.quick_actions

    def test_get_all_configs(self):
        configs = self.service.get_all_configs()
        assert len(configs) == 3

    def test_config_to_dict(self):
        config = self.service.get_config(PersonaType.SALES)
        d = config.to_dict()
        assert d["persona"] == "sales"
        assert "widgets" in d
        assert "quick_actions" in d

    def test_all_personas_have_configs(self):
        for persona in PersonaType:
            assert persona in PERSONA_CONFIGS
