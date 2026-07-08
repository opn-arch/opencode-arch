# Project README

| Field | Value |
|---|---|
| Version | 1.0-draft |
| Date | 2026-07-08 |
| Project | OpenCode Architecture Extension |
| System | Knowledge OS (logs-db) |
| Author | TBD |

## Revision History

| Version | Date | Description |
|---|---|---|
| 1.0-draft | 2026-07-08 | Initial draft from automated analysis |

---

## 1. Project Overview

Knowledge OS is a **FastAPI-based knowledge management system** that captures, enriches, and retrieves development knowledge from engineering sessions. It serves as the backend for an OpenCode MCP extension providing:

- **Architecture context compression** — distills large codebases into LLM-consumable context windows
- **Validation tools** — verifies generated code against architectural constraints
- **Regen-loop orchestrator with blind mode** — drives iterative LLM code regeneration without human intervention
- **Learning loop** — captures regeneration outcomes to improve future generation quality

The system targets a solo developer workflow where decisions, logs, and architectural knowledge accumulate over time and remain searchable and actionable. The primary success metric is **time-to-insight < 30 seconds** for any historical decision.

### Live System Metrics

| Metric | Value |
|---|---|
| Total logs | 0 |
| Database tables | 66 |
| Latest migration | 056 |
| Python source files | 448 |
| Test files | 148 |
| API routers | 30 |
| SQLAlchemy models | 30 |
| HTML templates | 18 |

---

## 2. Architecture

### High-Level Architecture

The system decomposes into six functional blocks spanning ingestion, enrichment, knowledge management, API serving, data integrity, and documentation generation.

```mermaid
graph TB
    subgraph External
        USER[Solo Developer]
        LLM[LLM Copilot]
        OC[OpenCode Extension]
    end

    subgraph "Knowledge OS (logs-db)"
        subgraph "F4: Serve API & UI"
            API[FastAPI Routers<br/>30 endpoints]
            UI[HTML Templates<br/>18 templates]
        end

        subgraph "F1: Ingest Source Data"
            ING[Ingestion Pipeline<br/>11 modules]
        end

        subgraph "F2: Enrich Log Entities"
            ENR[Enrichment Engine<br/>6 modules]
        end

        subgraph "F3: Manage Knowledge Base"
            KB[Knowledge Base<br/>8 modules]
        end

        subgraph "F5: Maintain Data Integrity"
            DI[Data Integrity<br/>61 modules]
        end

        subgraph "F6: Generate Documentation"
            DOC[Doc Generator<br/>8 modules]
        end

        DB[(PostgreSQL<br/>66 tables)]
    end

    USER --> API
    USER --> UI
    LLM --> API
    OC --> API

    API --> ING
    API --> ENR
    API --> KB
    API --> DOC

    ING --> DB
    ENR --> DB
    KB --> DB
    DI --> DB
    DOC --> KB
```

### Functional Block Summary

| Block | Status | Modules | Responsibility |
|---|---|---|---|
| F1: Ingest Source Data | [ACTIVE] | 11 | Capture raw logs, session data, codebase observations |
| F2: Enrich Log Entities | [ACTIVE] | 6 | Tag, classify, and link entities post-ingestion |
| F3: Manage Knowledge Base | [ACTIVE] | 8 | CRUD operations on knowledge artifacts, search, retrieval |
| F4: Serve API & UI | [ACTIVE] | 53 | HTTP endpoints, HTML rendering, authentication |
| F5: Maintain Data Integrity | [ACTIVE] | 61 | Migrations, constraints, validation, referential integrity |
| F6: Generate Documentation | [ACTIVE] | 8 | Produce SE artifacts, ADRs, and system documentation |

### Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.x |
| Web Framework | FastAPI / Uvicorn |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Migrations | Alembic (56 migrations) |
| Templating | HTML (Jinja2) |
| Testing | pytest |
| Integration | OpenCode MCP protocol |

---

## 3. Entity Model

The system contains **30 SQLAlchemy models** spanning 66 database tables (including junction tables and supporting structures). Models are grouped by domain below.

> For complete schema details including columns, constraints, and junction tables, see the **Data Dictionary** artifact.

### Core Knowledge Domain

| Model | Description |
|---|---|
| Log | Primary knowledge unit capturing session observations and decisions |
| Entity | Named concept extracted from logs (person, technology, project, etc.) |
| Tag | Classification label applied to logs and entities |
| Comment | Annotation attached to any knowledge artifact |
| Category | Hierarchical grouping for log organization |

### Project & Architecture Domain

| Model | Description |
|---|---|
| Project | Software project tracked within the knowledge base |
| Technology | Technology or tool tracked for radar/adoption status |
| Pipeline | Automated process or workflow definition |
| PipelineEvent | Recorded execution event from a pipeline run |

### Development Workflow Domain

| Model | Description |
|---|---|
| Session | Development session capturing temporal context |
| Decision | Architecture decision record with status tracking |
| Requirement | Traceable requirement with priority and acceptance criteria |

### Relationships & Enrichment Domain

| Model | Description |
|---|---|
| EntityRelationship | Typed connection between two entities |
| LogEntity | Junction linking logs to extracted entities |
| SystemTechnology | Junction linking systems to their technology stack |
| TechnologyProject | Junction linking technologies to projects |

### LLM & Regeneration Domain

| Model | Description |
|---|---|
| LLMFeedback | Captured feedback from LLM generation cycles |
| RegenResult | Outcome record from blind-mode regeneration loops |
| ContextSnapshot | Compressed architecture context for LLM consumption |

### Remaining Models

| Model | Description |
|---|---|
| [TBD] | 11 additional models exist per manifest (30 total) — names pending model verification |

> **Note:** Only models verifiable from provided context are listed. The manifest confirms 30 SQLAlchemy models total. See Data Dictionary for the complete enumeration.

---

## 4. Getting Started

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.x (specific version [TBD]) |
| PostgreSQL | [TBD] |
| pip / Poetry | [TBD] |

### Installation

```bash
# Clone repository
git clone [TBD: repository URL]
cd logs-db

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # [TBD: confirm package manager]
```

### Configuration

Create a `.env` file with required environment variables:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/logs_db
# Additional configuration [TBD]
```

### Database Setup

```bash
# Run all 56 Alembic migrations
alembic upgrade head
```

### First Run

```bash
# Start the FastAPI application
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

> For production deployment, Docker configuration, and service dependencies, see the **Deployment Guide** artifact.

---

## 5. API Reference

The system exposes **30 API routers** organized by domain. Key endpoint groups:

### Core CRUD Operations

| Router | Key Operations | Description |
|---|---|---|
| `/logs` | GET, POST, PUT, DELETE | Log entry management and search |
| `/entities` | GET, POST, PUT, DELETE | Entity CRUD with relationship management |
| `/tags` | GET, POST, PUT, DELETE | Tag management and assignment |
| `/projects` | GET, POST, PUT, DELETE | Project tracking |
| `/technologies` | GET, POST, PUT, DELETE | Technology radar entries |
| `/pipelines` | GET, POST | Pipeline definitions and event recording |
| `/sessions` | GET, POST | Development session tracking |
| `/categories` | GET, POST, PUT, DELETE | Hierarchical category management |
| `/comments` | GET, POST, PUT, DELETE | Annotation management |

### Knowledge & Search

| Router | Key Operations | Description |
|---|---|---|
| `/search` | GET | Full-text and filtered search across knowledge base |
| `/knowledge-base` | GET | Aggregated knowledge retrieval |
| `/decisions` | GET, POST | Architecture decision records |

### LLM Integration & Regen Loop

| Router | Key Operations | Description |
|---|---|---|
| `/context` | GET | Compressed architecture context for LLM consumption |
| `/regen` | POST | Trigger regeneration loop (supports blind mode) |
| `/feedback` | GET, POST | LLM feedback capture and retrieval |
| `/validation` | POST | Validate generated code against architecture |

### Documentation & Artifacts

| Router | Key Operations | Description |
|---|---|---|
| `/artifacts` | GET, POST | SE artifact generation and retrieval |
| `/templates` | GET | HTML template rendering |

> **Note:** 30 routers confirmed via manifest. Specific route paths are representative based on functional architecture. See **ICD** artifact for complete interface contracts.

---

## 6. Testing

### Running Tests

```bash
# Run full test suite
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific category
pytest tests/unit/
pytest tests/integration/
```

### Test Metrics

| Metric | Value |
|---|---|
| Test files | 148 |
| Testing framework | pytest |
| CI integration | [TBD] |
| Coverage target | [TBD] |

### Testing Strategy

The test suite follows a layered approach:

```mermaid
graph LR
    subgraph "Test Pyramid"
        U[Unit Tests<br/>Model & utility validation]
        I[Integration Tests<br/>Router & DB interaction]
        S[System Tests<br/>End-to-end workflows]
        A[Acceptance Tests<br/>Stakeholder scenarios]
    end

    U --> I --> S --> A
```

- **Unit tests** — Validate models, schemas, utility functions in isolation
- **Integration tests** — Exercise FastAPI routes with test database
- **System tests** — End-to-end pipeline and regeneration loop verification
- **Acceptance tests** — Validate against stakeholder success metrics

Fixtures are managed via `conftest.py` with SQLAlchemy test sessions and factory patterns.

> For detailed test architecture, mocking patterns, and CI configuration, see the **Testing** artifact.

---

## 7. Project Structure

```
logs-db/
├── app/                        # Application source (448 Python files)
│   ├── main.py                 # FastAPI application entry point
│   ├── routers/                # API route handlers (30 routers)
│   ├── models/                 # SQLAlchemy ORM models (30 models)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer
│   ├── pipelines/              # Ingestion and enrichment pipelines
│   ├── templates/              # HTML templates (18 files)
│   └── utils/                  # Shared utilities
├── migrations/                 # Alembic migrations (001–056)
│   ├── versions/               # Migration scripts
│   └── env.py                  # Migration environment config
├── tests/                      # Test suite (148 test files)
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── conftest.py             # Shared fixtures
├── docs/                       # Documentation artifacts
├── alembic.ini                 # Alembic configuration
├── .env                        # Environment variables (not committed)
└── requirements.txt            # Python dependencies [TBD: confirm]
```

### Directory Responsibilities

| Directory | Purpose | File Count |
|---|---|---|
| `app/` | All application source code | 448 files |
| `app/routers/` | HTTP endpoint definitions | 30 routers |
| `app/models/` | Database ORM layer | 30 models |
| `app/templates/` | Server-rendered HTML | 18 templates |
| `migrations/versions/` | Schema evolution scripts | 56 migrations |
| `tests/` | Automated test suite | 148 files |

---

## Cross-Reference Index

| Artifact | Relevance |
|---|---|
| Data Dictionary | Complete entity schema, columns, constraints, enumerations |
| Deployment Guide | Production setup, Docker, service dependencies |
| ICD | Full API contracts, protocol specifications, data formats |
| Functional Architecture | Detailed block decomposition and data flows |
| Logical Architecture | Technology allocation and component mapping |
| Operations Manual | Day-to-day procedures, monitoring, SOPs |
| Testing | Detailed test strategy, coverage analysis, CI configuration |
| System Vision | Long-term roadmap and design principles |