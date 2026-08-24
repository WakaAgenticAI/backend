create table public.chat_sessions (
  id uuid primary key default extensions.uuid_generate_v4(),
  user_id uuid references public.profiles(id),
  language text default 'en',
  created_at timestamptz not null default now()
);

create table public.chat_messages (
  id uuid primary key default extensions.uuid_generate_v4(),
  session_id uuid references public.chat_sessions(id) on delete cascade,
  sender text not null check (sender in ('user','agent')),
  content text not null,
  intent text,
  agent text,
  audio_url text,
  created_at timestamptz not null default now()
);

create table public.support_tickets (
  id uuid primary key default extensions.uuid_generate_v4(),
  chat_session_id uuid references public.chat_sessions(id),
  created_by uuid references public.profiles(id),
  status text default 'open' check (status in ('open','pending','resolved')),
  sla_due_at timestamptz,
  created_at timestamptz not null default now()
);

create index idx_chat_messages_session on public.chat_messages(session_id, created_at);
create index idx_chat_sessions_user on public.chat_sessions(user_id);
create index idx_support_tickets_created_by on public.support_tickets(created_by);
