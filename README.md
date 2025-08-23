# WakaAgent AI — Backend (FastAPI Modular Monolith)

A modular FastAPI backend for WakaAgent AI (Agentic AI-powered Distribution Management System). It provides JWT-secured APIs, realtime updates, and scaffolding for agents, CRM, orders, inventory with AI forecasts, finance + fraud, and support modules.

This repo is structured for incremental growth: start as a modular monolith and evolve to services later. Includes pytest + coverage, conda environment, and a demo script.

---

## Documentation

- Frontend (Vercel) Deployment — `docs/frontend-vercel-deploy.md`
- Backend (Render) Deployment — `docs/backend-render-deploy.md`
- Database Explanation — `docs/database-explanation.md`
- MCP Usage Guide — `docs/mcp-usage-guide.md`
- Product Guide — `docs/product-guide.md`

---

## Features

- **FastAPI** app with versioned routing and CORS
- **Modular structure**: `api`, `core`, `models`, `services`, `utils`, `db`, `agents`
- **Config** via `.env` (Pydantic Settings)
- **DB ready**: SQLAlchemy engine + session factory (PostgreSQL URL)
- **Testing**: pytest + coverage wired via `pyproject.toml`
- **Environment**: `environment.yaml` for conda
- **Demo**: `api_demo.py` hits health and diagnostics endpoints
- **AI**: Groq API integration (`/api/v1/ai/complete`) using `groq` Python SDK

---

## Project Layout

```
backend/
  app/
    api/
      v1/
        endpoints/
          health.py
          testall.py
      router.py
    core/
      config.py
    db/
      session.py
    models/
      base.py
    services/
    agents/
    schemas/
    utils/
    __init__.py
    main.py
  tests/
    conftest.py
    test_health.py
  api_demo.py
  .env_example
  pyproject.toml
  setup.py
  environment.yaml
  README.md
```

---

## Getting Started

### 1) Create the Conda environment

```
conda env create -f environment.yaml
conda activate wakaagent-backend
```

If you prefer venv/pip, install dependencies using `pyproject.toml`:

```
pip install -e .
# or
pip install -e .[dev]
```

### 2) Configure environment

Copy `.env_example` to `.env` and adjust values:

```
cp .env_example .env
```

Key settings (see `app/core/config.py`):
- `DATABASE_URL` (PostgreSQL)
- `REDIS_URL`
- `CORS_ORIGINS`
- `JWT_SECRET`
- Optional AI services: `OLLAMA_HOST`, `WHISPER_HOST`
- Groq AI: `GROQ_API_KEY`, `GROQ_MODEL` (default: `llama3-8b-8192`)

### 3) Run the API locally

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Docs: http://localhost:8000/api/v1/docs

Health: `GET /api/v1/healthz`  |  Ready: `GET /api/v1/readyz`
AI: `POST /api/v1/ai/complete` (set `GROQ_API_KEY`)

### 4) Try the demo script

```
python api_demo.py --base http://localhost:8000/api/v1

# Optionally exercise AI (requires GROQ_API_KEY in environment)
python api_demo.py --base http://localhost:8000/api/v1 --ai "Summarize WakaAgent in one sentence."
```

Expected output shows 200s for `/healthz`, `/readyz`, and `/demo/testall` plus basic environment info (secrets redacted).

---

## Testing & Coverage

Run tests:

```
pytest
```

Run with coverage (preconfigured):

```
pytest --cov=app --cov-report=term-missing
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

## Modularity & Where to Add Code

- **API routes** → `app/api/v1/endpoints/*.py` and register in `app/api/router.py`
- **Business logic (domain)** → `app/services/` (e.g., `orders_service.py`, `crm_service.py`)
- **Agent workflows** → `app/agents/` (e.g., LangGraph orchestrator, tools)
- **Database models** → `app/models/` with base in `base.py`
- **DB session & migrations** → `app/db/session.py` (add Alembic later)
- **Schemas (Pydantic)** → `app/schemas/` (request/response models)
- **Utilities** → `app/utils/` (logging, helpers)
- **Config** → `app/core/config.py`

---

## API Surface (current)

- `GET /api/v1/healthz` — liveness check
- `GET /api/v1/readyz` — readiness (extend with DB/Redis checks)
- `GET /api/v1/demo/testall` — diagnostics with environment info
- `POST /api/v1/ai/complete` — small completion using Groq LLM

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
- Socket.IO is mounted under path `/ws` and namespace `/chat` (see `app.realtime.server.Realtime`).
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

- Add Alembic migrations and initial models per PRD tables.
- Implement auth refresh flow in frontend using `POST /auth/refresh`.
- Optionally restrict CORS more tightly per environment.
- Mount static route for reports (see above) or upload exports to object storage (S3/GCS) and return signed URLs.
- Expand tests: API contract tests, service unit tests, integration tests.

---

## License

Proprietary © WakaAgent AI
