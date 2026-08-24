# Archive

Historical code that is **not** part of the running product.

| Path | What it was |
|---|---|
| `fastapi-backend/` | Original FastAPI + Uvicorn + Socket.IO + Alembic backend (Render). Replaced by `../supabase/`. |

Do not deploy anything in this folder. The live backend is Supabase (`../supabase/`). The Next.js app talks to it with `supabase-js`.
