"""
Persona-Driven Views (PRD 4.9)

Architectural Intent:
- Defines persona types and their dashboard configurations
- Personas: Sales, Presales, Delivery
- Each persona sees different metrics, alerts, and actions

MCP Integration:
- Resources: persona://{persona_type}/dashboard
- Prompts: persona_briefing for generating persona-specific summaries

Parallelization Strategy:
- Dashboard data for different widgets loads concurrently
"""

from dataclasses import dataclass, field
from enum import Enum


class PersonaType(Enum):
    SALES = "sales"
    PRESALES = "presales"
    DELIVERY = "delivery"


@dataclass(frozen=True)
class DashboardWidget:
    """Configuration for a single dashboard widget."""
    id: str
    title: str
    widget_type: str  # "metric", "chart", "list", "status"
    data_source: str  # API endpoint or resource URI
    priority: int = 0


@dataclass(frozen=True)
class PersonaConfig:
    """Dashboard configuration for a specific persona."""
    persona: PersonaType
    display_name: str
    description: str
    widgets: tuple[DashboardWidget, ...]
    quick_actions: tuple[str, ...] = field(default_factory=tuple)
    alert_categories: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "persona": self.persona.value,
            "display_name": self.display_name,
            "description": self.description,
            "widgets": [
                {"id": w.id, "title": w.title, "type": w.widget_type, "data_source": w.data_source}
                for w in self.widgets
            ],
            "quick_actions": list(self.quick_actions),
            "alert_categories": list(self.alert_categories),
        }


PERSONA_CONFIGS = {
    PersonaType.SALES: PersonaConfig(
        persona=PersonaType.SALES,
        display_name="Sales Dashboard",
        description="Revenue-focused view with deal tracking and customer metrics",
        widgets=(
            DashboardWidget("revenue", "Monthly Revenue", "metric", "/api/costs/summary", 1),
            DashboardWidget("deals", "Active Deals", "metric", "/api/deals/active", 2),
            DashboardWidget("customers", "Customer Health", "list", "/api/customers/health", 3),
            DashboardWidget("pipeline", "Sales Pipeline", "chart", "/api/deals/pipeline", 4),
        ),
        quick_actions=("create_proposal", "schedule_demo", "generate_roi_report"),
        alert_categories=("deal_risk", "renewal", "upsell_opportunity"),
    ),
    PersonaType.PRESALES: PersonaConfig(
        persona=PersonaType.PRESALES,
        display_name="Presales Dashboard",
        description="Technical assessment and cloud readiness focused view",
        widgets=(
            DashboardWidget("readiness", "Cloud Readiness Scores", "list", "/api/readiness/scores", 1),
            DashboardWidget("assessments", "Active Assessments", "metric", "/api/assessments/active", 2),
            DashboardWidget("architecture", "Architecture Reviews", "list", "/api/reviews/pending", 3),
            DashboardWidget("templates", "Solution Templates", "list", "/api/templates", 4),
        ),
        quick_actions=("start_assessment", "generate_architecture_diagram", "create_migration_plan"),
        alert_categories=("assessment_due", "architecture_risk", "compatibility_issue"),
    ),
    PersonaType.DELIVERY: PersonaConfig(
        persona=PersonaType.DELIVERY,
        display_name="Delivery Dashboard",
        description="Migration execution and operational health view",
        widgets=(
            DashboardWidget("migrations", "Active Migrations", "list", "/api/migrations/active", 1),
            DashboardWidget("resources", "Resource Health", "status", "/api/resources/health", 2),
            DashboardWidget("velocity", "Migration Velocity", "chart", "/api/migrations/velocity", 3),
            DashboardWidget("incidents", "Open Incidents", "list", "/api/incidents/open", 4),
            DashboardWidget("costs", "Cost Tracking", "metric", "/api/costs/current", 5),
        ),
        quick_actions=("deploy_resources", "run_migration_wave", "rollback_deployment"),
        alert_categories=("migration_blocked", "resource_unhealthy", "cost_overrun", "sla_breach"),
    ),
}


class PersonaService:
    """Service for managing persona-driven dashboard configurations."""

    def get_config(self, persona: PersonaType) -> PersonaConfig:
        return PERSONA_CONFIGS[persona]

    def get_all_configs(self) -> list[PersonaConfig]:
        return list(PERSONA_CONFIGS.values())

    def get_dashboard_data(self, persona: PersonaType) -> dict:
        """Get structured dashboard data for a persona."""
        config = self.get_config(persona)
        return {
            "persona": config.to_dict(),
            "data": {},  # Populated by presentation layer with actual API calls
        }
