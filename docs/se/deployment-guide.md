# Deployment Guide

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

## 1. Prerequisites

### Hardware Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8 cores (for Ollama inference) |
| RAM | 8 GB | 16 GB |
| Disk | 20 GB | 50 GB (model weights + embeddings cache) |
| GPU | None (CPU inference supported) | NVIDIA GPU w/ 8GB VRAM |

### Software Dependencies

#### Runtime [ACTIVE]

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Application runtime |
| PostgreSQL | 16 | Primary data store (IFC-003) |
| pgvector | 0.8.3 | Vector similarity search extension |
| Java | 11+ | PlantUML rendering engine |

#### AI/ML Services [ACTIVE]

| Dependency | Version | Purpose |
|---|---|---|
| Ollama | Latest stable | Local LLM inference (qwen2.5:7b) |
| copilot-relay server | [TBD] | LLM proxy for enrichment (IFC-001) |
| HuggingFace sentence-transformers | Cached locally | Embedding generation (IFC-004) |

#### Tools [ACTIVE]

| Dependency | Version | Purpose |
|---|---|---|
| Graphviz | 2.43+ | PlantUML graph rendering dependency |
| Chrome/Chromium | Latest | PDF rendering for documentation |
| Docker | 24+ | Containerized deployment |
| Docker Compose | 2.20+ | Service orchestration |

---

## 2. Environment Setup

### Configuration Files

The system uses the following configuration files (verified in manifest):

| File | Purpose | Status |
|---|---|---|
| `.env.example` | Template for environment variables | [ACTIVE] |
| `alembic.ini` | Database migration configuration | [ACTIVE] |
| `pyproject.toml` | Python project/dependency definition | [ACTIVE] |
| `requirements.txt` | Pinned dependency list | [ACTIVE] |
| `Dockerfile` | Container image definition | [ACTIVE] |
| `docker-compose.yml` | Multi-service orchestration | [ACTIVE] |

### Environment Variables

Copy `.env.example` to `.env` and configure the following variables, mapped to their respective interface contracts:

| Variable | IFC Reference | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | IFC-003 (PostgreSQL) | PostgreSQL connection string with pgvector | `postgresql+asyncpg://user:pass@localhost:5432/logs_db` |
| `ECHO_API_URL` | IFC-001 (copilot-relay) | Base URL for copilot-relay LLM proxy | `http://localhost:8081` |
| `OLLAMA_BASE_URL` | IFC-002 (Ollama) | Ollama REST API endpoint | `http://localhost:11434` |
| `HF_HUB_OFFLINE` | IFC-004 (embedding model) | Force offline mode for HuggingFace Hub | `1` |
| `TRANSFORMERS_OFFLINE` | IFC-004 (embedding model) | Prevent model downloads at runtime | `1` |

#### Additional Variables

| Variable | Description | Default |
|---|---|---|
| `APP_HOST` | Uvicorn bind address | `0.0.0.0` |
| `APP_PORT` | Uvicorn bind port | `8000` |
| `ONENOTE_CLIENT_ID` | Microsoft Graph app registration (IFC-005) | [TBD] |
| `ONENOTE_CLIENT_SECRET` | Microsoft Graph secret (IFC-005) | [TBD] |
| `OURA_ACCESS_TOKEN` | Oura Ring API token (IFC-017) | [TBD] |

```mermaid
flowchart LR
    subgraph env[".env Configuration"]
        DB[DATABASE_URL]
        ECHO[ECHO_API_URL]
        OLL[OLLAMA_BASE_URL]
        HF1[HF_HUB_OFFLINE]
        HF2[TRANSFORMERS_OFFLINE]
    end

    DB -->|IFC-003| PG[(PostgreSQL + pgvector)]
    ECHO -->|IFC-001| CR[copilot-relay]
    OLL -->|IFC-002| OL[Ollama]
    HF1 -->|IFC-004| EM[Embedding Model]
    HF2 -->|IFC-004| EM
```

---

## 3. Installation

### Step 1: Clone Repository

```bash
git clone [TBD: repository URL]
cd logs-db
```

### Step 2: Create Environment File

```bash
cp .env.example .env
# Edit .env with appropriate values per Section 2
```

### Step 3: Install Python Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Start Infrastructure Services

```bash
docker compose up -d postgres ollama
```

### Step 5: Install pgvector Extension

```bash
docker compose exec postgres psql -U postgres -d logs_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 6: Run Database Migrations

The system has 56 Alembic migrations (latest: 056).

```bash
alembic upgrade head
```

### Step 7: Pull Ollama Model

```bash
ollama pull qwen2.5:7b
```

### Step 8: Cache Embedding Model

Run once with internet access to cache sentence-transformers locally:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

After caching, set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.

### Step 9: Start Application

```bash
uvicorn app.main:app --host $APP_HOST --port $APP_PORT
```

### Docker-based Full Deployment (Alternative)

```bash
docker compose up -d
```

---

## 4. Service Dependencies

```mermaid
flowchart TD
    subgraph F1["F1: Ingest Source Data"]
        F1a[OneNote/OneDrive Sync]
        F1b[Oura API Ingest]
    end

    subgraph F2["F2: Enrich Log Entities"]
        F2a[LLM Enrichment]
    end

    subgraph F3["F3: Manage Knowledge Base"]
        F3a[CRUD Operations]
    end

    subgraph F4["F4: Serve API & UI"]
        F4a[FastAPI + Templates]
    end

    subgraph F5["F5: Maintain Data Integrity"]
        F5a[Embedding Sync]
    end

    subgraph F6["F6: Generate Documentation"]
        F6a[Doc Generation]
    end

    F1a -->|IFC-005| OD[OneDrive/OneNote API]
    F1b -->|IFC-017| OURA[Oura API]
    F2a -->|IFC-001| CR[copilot-relay]
    F2a -->|IFC-002| OLL[Ollama]
    F3a -->|IFC-003| PG[(PostgreSQL)]
    F4a -->|IFC-003| PG
    F5a -->|IFC-003| PG
    F5a -->|IFC-004| EM[Embedding Model]
    F6a -->|IFC-001| CR
```

### Verification Commands by F-block

| F-block | Service | Verification Command | Expected Result |
|---|---|---|---|
| F1 | OneDrive/OneNote (IFC-005) | `curl -s https://graph.microsoft.com/v1.0/me` | HTTP 200 with valid token |
| F1 | Oura API (IFC-017) | `curl -s https://api.ouraring.com/v2/usercollection/daily_activity` | HTTP 200 |
| F2 | copilot-relay (IFC-001) | `curl -s $ECHO_API_URL/health` | `{"status": "ok"}` |
| F2 | Ollama (IFC-002) | `curl -s $OLLAMA_BASE_URL/api/tags` | JSON with model list including `qwen2.5:7b` |
| F3, F4, F5 | PostgreSQL (IFC-003) | `pg_isready -h localhost -p 5432` | `accepting connections` |
| F5 | Embedding model (IFC-004) | `python -c "from sentence_transformers import SentenceTransformer; m=SentenceTransformer('all-MiniLM-L6-v2'); print(m.encode('test').shape)"` | `(384,)` |
| F6 | copilot-relay (IFC-001) | Same as F2 copilot-relay check | `{"status": "ok"}` |

---

## 5. Data Initialization

### Migration Execution

The database schema consists of 66 tables managed through 56 Alembic migrations:

```bash
# Verify current migration state
alembic current

# Apply all migrations
alembic upgrade head

# Verify final state
alembic current
# Expected: 056 (head)
```

### Schema Verification

```sql
-- Verify table count (expected: 66)
SELECT count(*) FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verify pgvector extension
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- Expected: 0.8.3
```

### Seed Data

[TBD: Specific seed data scripts and procedures. See Data Dictionary for complete schema details.]

```bash
# If seed scripts exist:
python -m app.scripts.seed_data  # [TBD: verify actual script path]
```

### Embedding Initialization

After base data is loaded, generate embeddings for existing entities:

```bash
python -m app.scripts.generate_embeddings  # [TBD: verify actual script path]
```

---

## 6. Verification

### Health Check Sequence

Execute in order — each step depends on the previous:

```mermaid
flowchart LR
    A[1. PostgreSQL] --> B[2. pgvector]
    B --> C[3. Migrations]
    C --> D[4. Ollama]
    D --> E[5. copilot-relay]
    E --> F[6. Application]
    F --> G[7. API Endpoints]
```

### Verification Checklist

| # | Check | Command | Expected |
|---|---|---|---|
| 1 | PostgreSQL running | `pg_isready` | "accepting connections" |
| 2 | pgvector loaded | `psql -c "SELECT 'test'::vector(3);"` | No error |
| 3 | Migrations applied | `alembic current` | `056 (head)` |
| 4 | Ollama responding | `curl $OLLAMA_BASE_URL/api/tags` | JSON with models |
| 5 | copilot-relay up | `curl $ECHO_API_URL/health` | HTTP 200 |
| 6 | App starts | `curl http://localhost:8000/docs` | Swagger UI HTML |
| 7 | API routers loaded | Count endpoints in `/openapi.json` | 30 routers registered |

### Smoke Test

```bash
# Verify API responds with correct model count
curl -s http://localhost:8000/openapi.json | python -c "
import json, sys
spec = json.load(sys.stdin)
paths = len(spec.get('paths', {}))
print(f'API paths discovered: {paths}')
assert paths > 0, 'No API paths found'
"
```

---

## 7. Backup & Rollback

### Pre-deployment Backup

```bash
# Full database dump before deployment
pg_dump -h localhost -U postgres -d logs_db \
  --format=custom --file=backup_$(date +%Y%m%d_%H%M%S).dump

# Record current migration version
alembic current > migration_state_pre_deploy.txt
```

### Rollback Procedures

#### Application Rollback

```bash
# Stop current application
docker compose down app  # or kill uvicorn process

# Restore previous code version
git checkout <previous-tag>
pip install -r requirements.txt

# Restart
uvicorn app.main:app --host $APP_HOST --port $APP_PORT
```

#### Database Rollback

```bash
# Downgrade to specific migration
alembic downgrade <target-revision>

# Full restore from backup (nuclear option)
pg_restore -h localhost -U postgres -d logs_db \
  --clean --if-exists backup_YYYYMMDD_HHMMSS.dump
```

#### Rollback Decision Matrix

| Scenario | Action | Data Loss Risk |
|---|---|---|
| App fails to start, DB unchanged | Git checkout + restart | None |
| Migration fails mid-apply | `alembic downgrade -1` | None |
| Migration applied, data corrupted | Restore from pg_dump | Potential (post-backup data) |
| Multiple migrations applied | `alembic downgrade <pre-deploy-rev>` | Schema-dependent |

---

## 8. Troubleshooting

### Common Issues

| Problem | Symptom | Resolution |
|---|---|---|
| pgvector not found | `ERROR: type "vector" does not exist` | `CREATE EXTENSION IF NOT EXISTS vector;` in target database |
| Ollama model missing | HTTP 404 on inference calls | `ollama pull qwen2.5:7b` |
| Embedding model download at runtime | Timeout/network errors | Pre-cache model, set `HF_HUB_OFFLINE=1` |
| Migration conflict | `alembic upgrade head` fails with branch error | `alembic heads` to identify branches, merge or resolve |
| Port conflict | `Address already in use` | Check for existing process: `lsof -i :8000` |
| copilot-relay unreachable | Enrichment pipeline hangs | Verify `ECHO_API_URL`, check relay process/container |
| Database connection refused | `Connection refused` on startup | Verify PostgreSQL is running and `DATABASE_URL` is correct |

### Diagnostic Commands

```bash
# Check all container statuses
docker compose ps

# View application logs
docker compose logs -f app

# Check database connectivity from app container
docker compose exec app python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'].replace('+asyncpg', ''))
with e.connect() as c:
    print(c.execute(text('SELECT version()')).scalar())
"

# Verify migration state matches expected
alembic check  # Should report "No new upgrade operations detected"
```

### Log Locations

| Component | Log Location |
|---|---|
| Application (uvicorn) | stdout / `docker compose logs app` |
| PostgreSQL | `docker compose logs postgres` |
| Ollama | `docker compose logs ollama` |
| Alembic migrations | stdout during `alembic upgrade` |

---

## Cross-References

| Topic | Artifact |
|---|---|
| Post-deployment operations | Operations Manual |
| Daily maintenance procedures | Maintenance Manual |
| Complete schema details | Data Dictionary |
| Interface contracts | ICD |
| Service architecture | Functional Architecture, Logical Architecture |