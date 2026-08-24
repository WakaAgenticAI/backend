# WakaAgent AI — Backend (Supabase)

This repository is the **Supabase** backend for [WakaAgenticAI/frontend](https://github.com/WakaAgenticAI/frontend).

Postgres schema, RLS, RPCs, storage, realtime, and Edge Functions live here. The Next.js app talks to it with `supabase-js` — there is no FastAPI process.

The previous FastAPI service is in `archive/fastapi-backend/` for reference.

## Local

```bash
supabase start
supabase status   # copy API URL + anon key into the frontend .env.local
supabase secrets set GROQ_API_KEY=your-groq-key
```

Seeded login: `admin@example.com` / `admin123`

## Hosted project

1. Create a project at [supabase.com](https://supabase.com)
2. `supabase login`
3. `supabase link --project-ref <ref>`
4. `supabase db push`
5. `supabase functions deploy`
6. `supabase secrets set GROQ_API_KEY=...`
7. Enable Email and Google providers
8. Set frontend env vars:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Never expose `SUPABASE_SERVICE_ROLE_KEY` to the browser.

Full design: see the `docs/supabase-backend.md` file in the local monorepo, or this folder's `README.md`.
