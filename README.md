# WakaAgent AI — Backend

FastAPI backend for WakaAgent AI — an AI-powered distribution management system for Nigerian businesses. Provides JWT-secured REST APIs, 7 AI agents, realtime Socket.IO, email notifications, and comprehensive business logic.

---

## Quick Start (for your deployment partner)

```bash
# 1. Clone and enter backend
git clone <repo-url>
cd WakaAgentAI/backend

# 2. Install Python dependencies with Poetry
poetry install

# 3. Copy and configure environment
cp .env_example .env
# Edit .env — see "Environment Variables" section below

# 4. Activate virtual environment
poetry shell

# 5. Start the server (SQLite works out of the box for local dev)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The app auto-seeds on first startup:
- **Admin user**: `admin@example.com` / `admin123`
- **Default roles**: Admin, Sales, Ops, Finance, Sales Representative, Stock Keeper
- **Sample products**: Apple, Bread, Milk with inventory

**API docs**: http://localhost:8000/api/v1/docs
**Health check**: http://localhost:8000/api/v1/healthz

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Poetry | latest | `curl -sSL https://install.python-poetry.org \| python3 -` |
| PostgreSQL | 16 (prod) | Docker or native install — SQLite works for dev |
| Redis | 7 (optional) | Only needed for Socket.IO multi-process scaling |

---

## Setup Options

### Option A: Poetry (Recommended)

```bash
cd backend
poetry install          # installs all deps from poetry.lock
poetry shell            # activates the virtual environment
```

### Option B: Conda

```bash
conda env create -f environment.yaml
conda activate wakaagent-backend
```

### Option C: pip + venv

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Environment Variables

Copy `.env_example` to `.env` and fill in:

```bash
cp .env_example .env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | `sqlite:///./app.db` | DB connection string. Use `postgresql+psycopg://user:pass@host:port/db` for production |
| `JWT_SECRET` | **Yes** | `change-me-in-prod` | Secret for JWT tokens — **must change in production** |
| `JWT_ALG` | No | `HS256` | JWT algorithm |
| `CORS_ORIGINS` | **Yes** | `http://localhost:3000` | Comma-separated allowed origins (add your frontend URL) |
| `APP_ENV` | No | `dev` | `dev` or `prod` — disables Swagger docs in prod |
| `API_V1_PREFIX` | No | `/api/v1` | API route prefix |
| `GROQ_API_KEY` | **Yes** | — | Groq API key from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model to use |
| `REDIS_URL` | No | — | Redis URL for Socket.IO scaling |
| `OLLAMA_HOST` | No | `http://localhost:11434` | Ollama fallback LLM |
| `WHISPER_HOST` | No | — | Whisper transcription service URL |
| `RESEND_API_KEY` | No | — | [Resend](https://resend.com) API key for email alerts |
| `ALERT_EMAIL_FROM` | No | `WakaAgent AI <alerts@resend.dev>` | Sender address for alerts |
| `ALERT_EMAIL_TO` | No | — | Recipient email for alerts |
| `EMAIL_NOTIFICATIONS_ENABLED` | No | `true` | Toggle email notifications on/off |
| `REPORTS_EXPORT_DIR` | No | `exports` | Directory for generated report files |

---

## Database

### Local Dev (SQLite — zero config)

The default `DATABASE_URL=sqlite:///./app.db` works immediately. No Postgres needed.

### Local Dev (PostgreSQL via Docker)

```bash
# Start Postgres only
docker compose up -d postgres

# Set in .env:
# DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/wakaagent

# Run migrations
alembic upgrade head
```

### Migrations (Alembic)

```bash
alembic upgrade head                              # apply all migrations
alembic current                                   # check current state
alembic revision -m "describe change" --autogenerate  # create new migration
alembic downgrade -1                              # rollback one step
```

---

## Docker

Full stack (Postgres + Redis + Backend):

```bash
cd backend
cp .env_example .env    # configure first
docker compose up -d

# Verify
curl http://localhost:8000/api/v1/healthz
```

Services started:
- **PostgreSQL 16** → port 5432
- **Redis 7** → port 6379
- **Backend API** → port 8000

---

## Deploy to Render

A `render.yaml` blueprint is included for one-click deployment.

### Step 1: Create Render Postgres

1. [Render Dashboard](https://dashboard.render.com) → **New** → **PostgreSQL**
2. Name: `wakaagent-db`, Plan: Free, Region: Oregon
3. After creation, copy the **Internal Database URL**

### Step 2: Deploy Backend

#### Option A: Blueprint (one-click)

1. Push repo to GitHub
2. Render → **New** → **Blueprint** → connect repo → select `backend/render.yaml`
3. Set environment variables (see Step 3)

#### Option B: Manual

1. Render → **New** → **Web Service** → connect repo
2. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: Python
   - **Build Command**: `pip install -U pip && pip install .`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/v1/healthz`

### Step 3: Set Environment Variables

In Render Dashboard → your service → **Environment**:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Render Postgres **Internal Database URL** |
| `JWT_SECRET` | Generate with `openssl rand -hex 32` |
| `CORS_ORIGINS` | Your Netlify frontend URL (e.g. `https://your-app.netlify.app`) |
| `GROQ_API_KEY` | From [console.groq.com](https://console.groq.com) |
| `APP_ENV` | `prod` |
| `RESEND_API_KEY` | From [resend.com](https://resend.com) (optional) |
| `ALERT_EMAIL_TO` | Your alert recipient email (optional) |

> Migrations run automatically on each deploy via `postDeployCommand: alembic upgrade head`.

---

## Email Notifications (Resend)

The app sends email alerts for critical business events using [Resend](https://resend.com) (free tier: 100 emails/day).

### Setup

1. Sign up at [resend.com](https://resend.com) → get API key
2. Add to `.env` (or Render env vars):
   ```
   RESEND_API_KEY=re_your_key_here
   ALERT_EMAIL_FROM=WakaAgent AI <alerts@resend.dev>
   ALERT_EMAIL_TO=your-email@example.com
   EMAIL_NOTIFICATIONS_ENABLED=true
   ```

### Alert Types

| Alert | Trigger | Description |
|-------|---------|-------------|
| Low Stock | Inventory agent check | Items below reorder point |
| Fraud Detection | Order risk analysis | Medium/high risk orders flagged |
| Overdue Debts | Debt status update | Newly overdue receivables/payables |
| Order Failure | Order processing error | Failed order creation |
| System Health | Manual trigger | Critical system warnings |

### Test via API

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Send test email
curl -X POST http://localhost:8000/api/v1/notifications/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"subject":"Test Alert","message":"Hello from WakaAgent!"}'

# Check notification status
curl http://localhost:8000/api/v1/notifications/status \
  -H "Authorization: Bearer $TOKEN"
```

---

## Testing

```bash
poetry shell

# Run all tests (300+ tests)
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_orders_service.py -v

# Lint & format
ruff check .
black .
mypy app
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/healthz` | No | Health check |
| POST | `/api/v1/auth/login` | No | Login → JWT tokens |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |
| GET | `/api/v1/auth/me` | Yes | Current user info |
| GET/POST | `/api/v1/orders` | Yes | List / create orders |
| POST | `/api/v1/orders/{id}/fulfill` | Yes | Fulfill an order |
| PATCH | `/api/v1/orders/{id}` | Yes | Update order status |
| GET/POST | `/api/v1/products` | Yes | List / create products |
| PATCH/DELETE | `/api/v1/products/{id}` | Yes | Update / delete product |
| GET/POST | `/api/v1/customers` | Yes | List / create customers |
| GET/POST | `/api/v1/inventory` | Yes | List / adjust inventory |
| GET | `/api/v1/warehouses` | Yes | List warehouses |
| GET/POST | `/api/v1/debts` | Yes | List / create debts |
| GET | `/api/v1/debts/reports/summary` | Yes | Debt summary |
| GET | `/api/v1/debts/reports/aging` | Yes | Aging report |
| POST | `/api/v1/chat/sessions` | Yes | Create chat session |
| POST | `/api/v1/chat/sessions/{id}/messages` | Yes | Send chat message |
| POST | `/api/v1/ai/complete` | Yes | LLM completion |
| POST | `/api/v1/ai/complete/stream` | Yes | Streaming LLM |
| POST | `/api/v1/ai/complete/rag` | Yes | RAG completion |
| POST | `/api/v1/ai/transcribe` | Yes | Voice transcription |
| POST | `/api/v1/ai/multilingual` | Yes | Multilingual processing |
| GET | `/api/v1/notifications/status` | Yes | Email config status |
| POST | `/api/v1/notifications/test` | Yes | Send test email |
| POST | `/api/v1/notifications/alert/*` | Yes | Trigger specific alerts |
| GET | `/api/v1/roles` | Yes | List roles |
| POST | `/api/v1/tools/execute` | Yes | Execute agent tools |

Full interactive docs: `http://localhost:8000/api/v1/docs`

---

## Realtime (Socket.IO)

- **Path**: `/ws`
- **Namespaces**: `/chat` (messages + KB suggestions), `/orders` (order updates)
- **Rooms**: `chat_session:<id>`, `order:<id>`
- **Redis**: Optional — set `REDIS_URL` for multi-process scaling

Nginx proxy config (if needed):
```nginx
location /ws/ {
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_pass http://backend:8000/ws/;
}
```

---

## Project Layout

```
backend/
├── app/
│   ├── agents/              # 7 LangGraph AI agents
│   │   ├── orchestrator.py  # Agent coordination & intent routing
│   │   ├── orders_agent.py
│   │   ├── orders_lookup_agent.py
│   │   ├── inventory_agent.py
│   │   ├── forecasting_agent.py
│   │   ├── fraud_detection_agent.py
│   │   ├── crm_agent.py
│   │   └── finance_agent.py
│   ├── api/v1/endpoints/    # REST API endpoints
│   │   ├── auth.py, orders.py, products.py, customers.py
│   │   ├── inventory.py, debts.py, reports.py, roles.py
│   │   ├── chat.py, ai.py, tools.py, notifications.py
│   │   └── health.py, forecasts.py, testall.py
│   ├── core/                # Config, security, middleware
│   ├── db/                  # SQLAlchemy session & engine
│   ├── jobs/                # Background tasks (Celery)
│   ├── kb/                  # ChromaDB knowledge base
│   ├── models/              # SQLAlchemy ORM models
│   ├── realtime/            # Socket.IO server & event emitters
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic
│   │   ├── orders_service.py, debt_service.py
│   │   ├── email_service.py, reports_service.py
│   │   ├── llm_client.py, whisper_client.py
│   │   ├── chroma_client.py, multilingual_client.py
│   │   └── ai/groq_client.py
│   └── main.py              # App factory + lifespan
├── alembic/                 # Database migrations
├── tests/                   # 300+ pytest tests
├── pyproject.toml           # Poetry deps & project config
├── poetry.lock              # Locked dependency versions
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yaml      # Postgres + Redis + Backend
├── render.yaml              # Render.com deployment blueprint
├── .env_example             # Environment variable template
└── api_demo.py              # Demo script for all endpoints
```

---

## Where to Add Code

| What | Where |
|------|-------|
| New API endpoint | `app/api/v1/endpoints/` → register in `app/api/router.py` |
| Business logic | `app/services/` |
| New AI agent | `app/agents/` → register in `app/main.py` lifespan |
| Database model | `app/models/` → create Alembic migration |
| Pydantic schema | `app/schemas/` |
| Background job | `app/jobs/` |
| Realtime event | `app/realtime/emitter.py` |

---

## License

Apache-2.0
