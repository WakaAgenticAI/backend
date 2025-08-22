# Project TODOs

- After you install psycopg and confirm, I’ll re-run migrations to create the chat tables.
- Then I can:
  - Add inventory endpoints and reservation on order create.
  - Add forecasts API and daily stub.
  - Add finance endpoints (reports/webhook) and minimal fraud checks.
  - Add audit_logs persistence, request ID middleware, and rate limiting.


completed: Implement Chatbot foundation slice.
in_progress: Install psycopg driver and rerun Alembic migrations.
in_progress: Inventory reservation + fulfill + endpoints.
pending: Autogenerate inventory migration and apply.
pending: Realtime Socket.IO + Redis (replace stub).
pending: Chatbot Phase 2 tools + embeddings/KB + emits.
pending: Start Docker, bring up Postgres, set DATABASE_URL, run Alembic upgrades.
pending: Persist audit logs to DB; request ID middleware; rate limiting.
pending: Ensure DATABASE_URL in .env; cleanup docker-compose version key.