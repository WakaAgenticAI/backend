create table public.reports (
  id uuid primary key default extensions.uuid_generate_v4(),
  kind text not null,
  period text,
  file_path text,
  status text default 'processing' check (status in ('processing','ready','failed')),
  requested_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create table public.audit_logs (
  id uuid primary key default extensions.uuid_generate_v4(),
  user_id uuid references public.profiles(id),
  action text not null,
  resource text not null,
  ip text,
  created_at timestamptz not null default now()
);

create index idx_reports_kind on public.reports(kind, created_at desc);
create index idx_audit_logs_user on public.audit_logs(user_id, created_at desc);
