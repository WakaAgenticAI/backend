# WakaAgent AI — Backend (FastAPI Modular Monolith)

A modular FastAPI backend for WakaAgent AI (Agentic AI-powered Distribution Management System). It provides JWT-secured APIs, realtime updates, and scaffolding for agents, CRM, orders, inventory with AI forecasts, finance + fraud, and support modules.

This repo is structured for incremental growth: start as a modular monolith and evolve to services later. Includes pytest + coverage, conda environment, and a demo script.

---

## Documentation

This README is the source of truth for backend setup and contribution. Additional docs will be added under a `docs/` directory in future iterations. For now, see:

- `scripts/render_cli.py` for Render API CLI helpers (requires `RENDER_API_KEY`).
- `tools/mcp_config.template.json` for MCP client configuration to access Render MCP server.

---

## Features

- **FastAPI** app with versioned routing and CORS
- **Modular structure**: `app/api`, `app/core`, `app/models`, `app/services`, `app/utils`, `app/db`, `app/agents`, `app/realtime`
- **Config** via `.env` using Pydantic Settings (`app/core/config.py`)
- **DB ready**: SQLAlchemy 2.x + Alembic migrations (PostgreSQL recommended)
- **Realtime**: Socket.IO mounted at `/ws` with namespaces `/orders` and `/chat` (optional Redis manager)
- **Testing**: pytest + coverage pre-wired via `pyproject.toml`
- **Environment**: `environment.yaml`/`environment.yml` for conda
- **Demo**: `api_demo.py` exercises health, auth, CRUD, reports, and AI endpoints
- **AI**: Complete agentic AI system with Groq/Ollama LLM, ChromaDB memory, Whisper transcription, multilingual support, and LangGraph orchestration
- **Debt Tracking**: Comprehensive receivables/payables management with aging reports, payment tracking, and AI-powered collection insights
- **Tasks**: Celery app scaffold present (`app/celery_app.py`) for future background jobs

---

## Project Layout

```
backend/
  app/
    api/
      v1/
        endpoints/
          ai.py
          auth.py
          chat.py
          customers.py
          debts.py
          health.py
          inventory.py
          orders.py
          products.py
          reports.py
          roles.py
          testall.py
        __init__.py
      router.py
    core/
      app_state.py
      audit.py
      config.py
      logging.py
      middleware.py
      security.py
      __init__.py
    db/
      session.py
      __init__.py
    models/
      base.py
      users.py
      roles.py
      products.py
      inventory.py
      orders.py
      audit.py
      reports.py
      __init__.py
    realtime/
      server.py
    agents/
      orchestrator.py
      inventory_agent.py
      orders_agent.py
      forecasting_agent.py
      fraud_detection_agent.py
      crm_agent.py
      finance_agent.py
      __init__.py
    schemas/
      ...
    services/
      llm_client.py
      whisper_client.py
      chroma_client.py
      multilingual_client.py
      groq_client.py
      debt_service.py
      ...
    utils/
      ...
    celery_app.py
    main.py
  alembic/
    env.py
    versions/
      <timestamp>_*.py
  tests/
    conftest.py
    test_*.py
  scripts/
    render_cli.py
  tools/
    mcp_config.template.json
  api_demo.py
  docker-compose.yaml
  .env_example
  pyproject.toml
  environment.yaml
  environment.yml
  README.md
```

---

## Getting Started

### 1) Create the environment

Using Conda (recommended):

```
conda env create -f environment.yaml
conda activate wakaagent-backend
```

Or with venv/pip using `pyproject.toml`:

```
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 2) Start required services (optional for local SQLite, recommended for Postgres)

Run Postgres locally with Docker:

```
docker compose up -d postgres
```

Then set `DATABASE_URL` accordingly (see next step). Default compose uses:
`postgresql+psycopg://postgres:postgres@localhost:5432/wakaagent`

### 3) Configure environment

Copy `.env_example` to `.env` and adjust values:

```
cp .env_example .env
```

Key settings (see `app/core/config.py`):
- `DATABASE_URL` (PostgreSQL DSN)
- `REDIS_URL` (optional; enables Redis manager for realtime)
- `CORS_ORIGINS`
- `JWT_SECRET`
- AI Services: `GROQ_API_KEY`, `OLLAMA_HOST`, `WHISPER_HOST`
- ChromaDB: `CHROMA_PERSIST_DIRECTORY` (default: `.chromadb`)
- Multilingual: Supports Nigerian Pidgin, Hausa, Yoruba, Igbo

### 4) Initialize the database (Alembic)

```
alembic upgrade head
```

This uses `alembic/env.py` to load `DATABASE_URL` from `app/core/config.py`.

### 5) Run the API locally

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docs: http://localhost:8000/api/v1/docs

Health: `GET /api/v1/healthz`  |  Ready: `GET /api/v1/readyz`

**AI Endpoints:**
- `POST /api/v1/ai/complete` — LLM completion with conversation memory
- `POST /api/v1/ai/complete/stream` — Streaming LLM responses
- `POST /api/v1/ai/complete/rag` — RAG-enhanced completions
- `POST /api/v1/ai/transcribe` — Voice transcription (Whisper)
- `POST /api/v1/ai/multilingual` — Multilingual processing
- `POST /api/v1/ai/classify-intent` — Intent classification
- `GET /api/v1/ai/capabilities` — AI system capabilities
- `GET /api/v1/ai/languages` — Supported languages

### 6) Try the demo script

```
python api_demo.py --base http://localhost:8000/api/v1

# Test all AI features (requires GROQ_API_KEY in environment)
python api_demo.py --base http://localhost:8000/api/v1 --ai-complete --ai-rag --ai-multilingual --ai-classify --ai-capabilities --ai-languages
```

The script also supports creating demo products/orders/customers and triggering reports.

---

## Testing & Coverage

Run tests:

```
pytest
```

Run with coverage (preconfigured in `pyproject.toml`):

```
pytest --cov=app --cov-report=term-missing
```

Lint/format/type-check:

```
ruff check .
black .
mypy app
```

---

## Frontend Companion (Next.js)

The frontend lives in `frontend/wakaagent-ai/` and pairs with this backend.

### Environment

- `NEXT_PUBLIC_API_BASE` — base URL to this backend (e.g., `http://localhost:8000/api/v1` or your Render URL)
- `NEXT_PUBLIC_DEMO_BEARER` — optional bearer token for demo-only persistence

Create `frontend/wakaagent-ai/.env.local`:

```
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
# NEXT_PUBLIC_DEMO_BEARER=eyJhbGci...
```

### Local Development

```bash
cd frontend/wakaagent-ai
npm i --legacy-peer-deps
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1 npm run dev
```

Open http://localhost:3000 (or the next available port if 3000 is busy).

CRM “Add Customer” performs a local add and then best‑effort POST to `/customers` with an Authorization header using either `localStorage.access_token` or `NEXT_PUBLIC_DEMO_BEARER`. Finance/Admin CSV exports include a UTF‑8 BOM for Excel.

### Deployment

See `docs/frontend-vercel-deploy.md` for a step‑by‑step Vercel guide.

---

## AI System Architecture

The backend includes a comprehensive agentic AI system with the following components:

### 🤖 **AI Agents**
- **Orchestrator** — LangGraph-based workflow coordination and intent classification
- **Orders Agent** — Order management, creation, fulfillment, and payment processing
- **Inventory Agent** — Stock management, reservations, and low-stock alerts
- **Forecasting Agent** — AI-powered demand forecasting and reorder point optimization
- **Fraud Detection Agent** — Transaction scoring and fraud pattern detection
- **CRM Agent** — Customer relationship management, segmentation, and ticket creation
- **Finance Agent** — Debt management, collections, and financial insights

### 🧠 **AI Services**
- **LLM Client** — Unified interface for Groq and Ollama providers with conversation memory
- **Whisper Client** — Voice transcription from URLs, files, or base64 audio data
- **ChromaDB Client** — Persistent conversation memory with semantic search
- **Multilingual Client** — Nigerian language support (Pidgin, Hausa, Yoruba, Igbo)

### 🔄 **Workflow Features**
- **Intent Classification** — Automatic routing of user requests to appropriate agents
- **Streaming Responses** — Real-time LLM response streaming
- **RAG (Retrieval Augmented Generation)** — Enhanced responses with knowledge base context
- **Conversation Memory** — Persistent chat history with semantic search capabilities
- **Multilingual Processing** — Language detection, translation, and culturally-aware responses

### 🛠 **Integration Points**
- **Real-time Updates** — Socket.IO integration for live AI responses
- **Authentication** — JWT-secured AI endpoints
- **Database Integration** — Direct access to business data for informed responses
- **Background Processing** — Celery integration for long-running AI tasks

---

## Modularity & Where to Add Code

- **API routes** → `app/api/v1/endpoints/*.py` and register in `app/api/router.py`
- **Business logic (domain)** → `app/services/` (e.g., `orders_service.py`, `crm_service.py`)
- **Agent workflows** → `app/agents/` (`orchestrator.py`, `inventory_agent.py`, etc.)
- **Realtime** → `app/realtime/server.py` (Socket.IO setup and emits)
- **Database models** → `app/models/` with base in `base.py`
- **DB session & migrations** → `app/db/session.py`, Alembic in `alembic/`
- **Schemas (Pydantic)** → `app/schemas/` (request/response models)
- **Utilities** → `app/utils/` (logging, helpers)
- **Config** → `app/core/config.py`

---

## API Surface (current)

- `GET /api/v1/healthz` — liveness check
- `GET /api/v1/readyz` — readiness
- `GET /api/v1/demo/testall` — diagnostics

**AI Endpoints:**
- `POST /api/v1/ai/complete` — LLM completion with conversation memory
- `POST /api/v1/ai/complete/stream` — Streaming LLM responses
- `POST /api/v1/ai/complete/rag` — RAG-enhanced completions
- `POST /api/v1/ai/transcribe` — Voice transcription (Whisper)
- `POST /api/v1/ai/multilingual` — Multilingual processing
- `POST /api/v1/ai/classify-intent` — Intent classification
- `GET /api/v1/ai/capabilities` — AI system capabilities
- `GET /api/v1/ai/languages` — Supported languages
- `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/me`
- `GET/POST /api/v1/products`, `GET /api/v1/products/{id}`, etc.
- `GET/POST /api/v1/customers`, `GET /api/v1/customers/{id}`, etc.
- `GET/POST /api/v1/orders`, `POST /api/v1/orders/{id}/fulfill`
- `GET /api/v1/warehouses`, `GET/POST /api/v1/inventory`
- `GET /api/v1/roles`
- User roles (admin): `GET /api/v1/users/{user_id}/roles`, `POST /api/v1/users/{user_id}/roles`, `DELETE /api/v1/users/{user_id}/roles`
- `POST /api/v1/tools/execute`
- Chat sessions: `POST /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{session_id}/messages`, `POST /api/v1/chat/sessions/{session_id}/messages`
- Reports (admin): `POST /api/v1/admin/reports/daily-sales`, `GET /api/v1/admin/reports/daily-sales/latest`,
  `POST /api/v1/admin/reports/monthly-audit`, `GET /api/v1/admin/reports/monthly-audit/latest`
- Debts: `GET/POST /api/v1/debts`, `GET /api/v1/debts/{id}`, `PUT /api/v1/debts/{id}`, `POST /api/v1/debts/{id}/payments`, `GET /api/v1/debts/reports/aging`, `GET /api/v1/debts/reports/summary`

---

## Importing PRD files

To keep product context close to code, copy the PRD files into `backend/`:

```
# from repository root
cp backendPRD.md backend/
cp "WakaAgent AI.pdf" backend/
```

---

## Production Guide

### Auth & Default Admin
- Seeded on startup (see `app/main.py`):
  - Email: `admin@example.com`
  - Password: `admin123`
- Login payload: `{ "email": string, "password": string }` → `POST /api/v1/auth/login`
- Returns `{ access_token, refresh_token, token_type }`. Frontend uses Bearer token in `Authorization` header.

### CORS Configuration
In `app/main.py`, CORS is configured via `CORSMiddleware` using `CORS_ORIGINS` env. For production, set explicit origins (not `*`):

```
export CORS_ORIGINS=https://your-frontend-domain
```

Backend code already sets:
- `allow_credentials=True/False` depending on your needs. For Bearer-token auth (no cookies), prefer `allow_credentials=False`.
- `allow_methods=["*"]`, `allow_headers=["*"]`.

### WebSockets (Socket.IO)
- Socket.IO is mounted under path `/ws` with namespaces `/orders` and `/chat` (see `app/realtime/server.py`).
- Ensure your reverse proxy supports upgrades:

Nginx example:
```
location /ws/ {
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_pass http://backend:8000/ws/;
}
```

### Reports: Downloadable Files
- Report builders write files into `REPORTS_EXPORT_DIR` (see `app/services/reports_service.py`).
- Endpoints `GET /admin/reports/daily-sales/latest` and `GET /admin/reports/monthly-audit/latest` return DB rows including `file_url` (server path).
- To make downloads public:
  1) Mount a static route to serve `REPORTS_EXPORT_DIR` (recommended):

  ```python
  # in app/main.py (after FastAPI app creation)
  from fastapi.staticfiles import StaticFiles
  from app.core.config import get_settings
  settings = get_settings()
  app.mount("/reports-files", StaticFiles(directory=settings.REPORTS_EXPORT_DIR), name="reports_files")
  ```

  2) Include a `download_url` in report responses (e.g., `https://api.yourdomain.com/reports-files/<filename>`). The frontend already opens `download_url` when present.

  Alternatively, add `GET /api/v1/reports/{id}/download` that returns `FileResponse` for the stored file.

### Frontend (Vercel) Environment
- Set this in Vercel → Project → Settings → Environment Variables and redeploy:
```
NEXT_PUBLIC_API_BASE=https://api.yourdomain.com/api/v1
```
The frontend derives the WebSocket origin from `NEXT_PUBLIC_API_BASE` automatically (`wss://api.yourdomain.com/ws`).

---

## Notes & Next Steps

### ✅ **Completed**
- ✅ Complete AI implementation with agentic architecture
- ✅ All AI endpoints functional with authentication
- ✅ Frontend integration with real-time AI features
- ✅ Comprehensive testing suite for AI components
- ✅ Documentation and deployment guides

### 🔄 **In Progress**
- Implement auth refresh flow in frontend using `POST /auth/refresh`
- Mount static route for reports (see above) or upload exports to object storage (S3/GCS) and return signed URLs

### 🚀 **Future Enhancements**
- Add Alembic migrations and initial models per PRD tables
- Optionally restrict CORS more tightly per environment
- Expand tests: API contract tests, service unit tests, integration tests
- Add more AI agents for specialized business functions
- Implement advanced RAG with domain-specific knowledge bases

---

## License

Apache-2.0
