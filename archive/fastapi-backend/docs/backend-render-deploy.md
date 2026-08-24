# Backend Deployment (Render) — Quick Start

This quick guide shows how to deploy `backend/` to Render using the included `backend/render.yaml` on the Free web service tier.

---

## 1) Prerequisites

- GitHub repo connected to Render
- Backend lives at `backend/`
- Python is managed by Render (no Docker required)

---

## 2) One‑click via render.yaml

Render will auto-detect `render.yaml` when you choose "New +" → "Blueprint" → select this repo.

The blueprint defines:
- Web Service `wakaagent-backend` (plan: `free`)
- Root dir: `backend/`
- Build: `pip install -U pip && pip install .`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/v1/healthz`
- Post‑deploy: `alembic upgrade head`
- Env vars to set: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, optional `GROQ_API_KEY`, `REDIS_URL`

---

## 3) Environment variables

Required (Render → Service → Environment):
- `DATABASE_URL`
  - For demo: `sqlite:///./app.db` (zero-cost, ephemeral)
  - For Postgres: `postgresql+psycopg://<user>:<pass>@<host>:5432/<db>`
- `JWT_SECRET` — strong random string
- `CORS_ORIGINS` — e.g. `https://your-frontend.vercel.app`

Optional:
- `GROQ_API_KEY` — to use `/ai/complete`
- `REDIS_URL` — enables Socket.IO Redis manager for multi-instance scaling

All config keys are defined in `app/core/config.py`.

---

## 4) Database migrations (Alembic)

The blueprint runs `alembic upgrade head` after each deploy. You can re-run manually:

```
# Render Shell
alembic upgrade head
```

---

## 5) Frontend integration

- Frontend env: `NEXT_PUBLIC_API_BASE=https://<your-service>.onrender.com/api/v1`
- WebSockets: derived automatically from API origin (`wss://<your-service>.onrender.com/ws`)
- Ensure backend `CORS_ORIGINS` includes your frontend domain(s)

---

## 6) Free tier caveats

- Free web service sleeps on inactivity → cold start on next request
- Ephemeral filesystem → files under `exports/` won’t persist across restarts; use S3/GCS for durable downloads in production
- Postgres: Render’s free tier may not be available; consider their starter tier or external Postgres

---

## 7) Troubleshooting

- 502/Unhealthy: check logs, verify `DATABASE_URL`, and migration status
- CORS errors: confirm `CORS_ORIGINS` and HTTPS scheme
- Realtime: works without `REDIS_URL` in single instance; add Redis for scale
