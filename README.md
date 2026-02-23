# Cockpit — Agentic Cloud Modernization Platform

Cockpit is an AI-powered cloud infrastructure management platform built with clean hexagonal architecture. It provides a unified control plane for managing multi-cloud resources (AWS, Azure, GCP) through an intelligent agent hierarchy, natural language co-pilot, and automated migration workflows.

## Architecture

```
Domain Layer          Application Layer       Infrastructure Layer     Presentation Layer
 (entities,            (use cases,             (adapters, repos,        (REST API,
  value objects,        queries,                MCP servers,             WebSocket,
  ports, services)      orchestration)          AI providers)            React UI)
```

**Key Principles**: DDD, Hexagonal/Clean Architecture, Immutable Domain Models, MCP-Native Integration, Parallelism-First Design

## Features

### Multi-Cloud Management
- Connect and manage AWS, Azure, and GCP providers
- Create, start, stop, and terminate infrastructure resources
- Cost analysis with provider-level breakdowns and forecasting

### HMAS Agent Hierarchy (PRD-Compliant)
- **L3 Executive**: EPA (Executive Planning Agent) — orchestrates all specialist agents
- **L2 Specialists**: RSA (Refactoring Strategy), FIA (Financial Insight), GA (Governance), MVA (Migration Velocity), DOA (Deployment Orchestration), PMA (Performance Monitoring)
- **L1 Workers**: Task-specific agents delegated by L2
- A2A Agent Cards for inter-agent communication
- Per-agent IAM with role-based permissions
- MCP OAuth 2.1 token authorization

### AI Co-Pilot
- Natural language infrastructure management
- Conversation history with multi-turn context
- Supports Claude, OpenAI, and Gemini providers
- Typed output schemas with validation
- Context window management with token budgeting

### Migration Factory
- 6-stage pipeline: Assess → Plan → Execute → Validate → Cutover → Complete
- Cloud Readiness scoring with 6R strategy recommendation (Rehost, Replatform, Refactor, Repurchase, Retire, Retain)
- Parallel workload execution within migration waves

### Security
- JWT authentication on all API endpoints
- bcrypt password hashing (PBKDF2 fallback)
- Rate limiting (120 req/min per IP)
- WebSocket authentication via token query parameter
- Timing-safe secret comparisons
- Credential masking in logs
- SCC Threat Detection with resource scanning and risk summaries
- CORS restricted to configured origins

### Observability (OTLP)
- OpenTelemetry-compatible tracing, metrics, and logging ports
- Distributed trace context propagation
- Pluggable backends (in-memory for dev, OTLP exporters for production)

### Persona-Driven Dashboards
- **Sales**: Revenue metrics, deal tracking, customer health
- **Presales**: Cloud readiness scores, architecture reviews, solution templates
- **Delivery**: Active migrations, resource health, velocity charts, incident tracking

### MCP Servers (6 Bounded Contexts)
Each server exposes Tools (writes), Resources (reads), and Prompts (AI patterns):
- `cloud-provider-service` — Provider CRUD and connection management
- `infrastructure-resource-service` — Resource lifecycle management
- `agent-service` — AI agent configuration and task execution
- `cost-service` — Cost analysis, forecasting, and budget alerts
- `observability-service` — Metrics, logs, traces, and alerting
- `iac-service` — Terraform and Ansible operations

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Framer Motion, Lucide Icons |
| **API** | FastAPI, WebSocket, Pydantic v2 |
| **AI** | Claude (Anthropic), GPT-4o (OpenAI), Gemini (Google), Vertex AI Agent Engine |
| **Auth** | JWT (PyJWT), bcrypt |
| **Database** | SQLAlchemy (PostgreSQL), In-memory adapters for dev |
| **Protocol** | MCP (Model Context Protocol), A2A (Agent-to-Agent) |
| **Observability** | OpenTelemetry (OTLP) |
| **IaC** | Terraform, Ansible |

## Quick Start

### Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export COCKPIT_SECRET_KEY="your-secret-key"
export ANTHROPIC_API_KEY="sk-..."  # optional, for AI copilot

# Run the API server
python -m presentation.api.main
```

The API will be available at `http://localhost:8000`. API docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm start
```

The UI will be available at `http://localhost:3000`.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `COCKPIT_SECRET_KEY` | JWT signing key | Random (ephemeral) |
| `COCKPIT_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:3000` |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | — |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o | — |
| `GEMINI_API_KEY` | Google API key for Gemini | — |
| `AI_PROVIDER` | Default AI provider (`claude`, `openai`, `gemini`) | `claude` |
| `GCP_PROJECT_ID` | GCP project for Vertex AI Agent Engine | — |

## Testing

```bash
# Run all tests (177 tests)
python -m pytest tests/ -v

# Run by layer
python -m pytest tests/domain/ -v        # Pure domain logic
python -m pytest tests/application/ -v    # Use cases with mocked ports
python -m pytest tests/infrastructure/ -v # Adapter integration tests
```

## Project Structure

```
cockpit/
├── domain/
│   ├── entities/          # Agent, Resource, CloudProvider, HMASAgents
│   ├── value_objects/     # Money, Credentials
│   ├── ports/             # AIProviderPort, RepositoryPorts, ObservabilityPorts
│   ├── services/          # CloudReadiness, MemoryBank, MigrationFactory,
│   │                        Personas, ThreatDetection, AgentIdentity
│   └── exceptions.py
├── application/
│   ├── commands/          # Use cases (Create, Connect, Activate, etc.)
│   ├── queries/           # Read-only query handlers
│   ├── orchestration/     # DAG workflow orchestrator with backpressure
│   └── services/          # AI Copilot service
├── infrastructure/
│   ├── adapters/          # InMemory repos, AI adapters (Claude/OpenAI/Gemini),
│   │                        Vertex AI, OTLP adapters
│   ├── mcp_servers/       # 6 MCP servers (one per bounded context)
│   ├── config/            # DI container
│   └── auth.py            # JWT + bcrypt authentication
├── presentation/
│   └── api/               # FastAPI routes, controllers, WebSocket
├── frontend/
│   └── src/               # React app with dashboard, copilot, modals
├── tests/                 # 177 tests across all layers
├── AUDIT.md               # Full audit report with all fixes documented
└── requirements.txt
```

## Audit Status

All critical, high, and medium issues resolved. See [AUDIT.md](AUDIT.md) for the complete audit report.

| Dimension | Status |
|---|---|
| Critical Bugs | 0 remaining |
| Security Issues | 0 remaining (1 deployment-level TLS item) |
| UI/UX Issues | 0 remaining |
| PRD Conformance | 12/12 items implemented |
| skill2026 Compliance | 7/7 rules satisfied |
| Test Coverage | 177 tests passing |

## License

Proprietary. All rights reserved.
