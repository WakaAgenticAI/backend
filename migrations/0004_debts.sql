create table public.debts (
  id uuid primary key default extensions.uuid_generate_v4(),
  type text not null check (type in ('receivable','payable')),
  entity_type text not null check (entity_type in ('customer','supplier','other')),
  entity_id uuid,
  amount_ngn numeric(15,2) not null,
  currency text default 'NGN',
  description text,
  due_date date,
  status text default 'pending' check (status in ('pending','partial','paid','overdue','cancelled')),
  priority text default 'medium' check (priority in ('low','medium','high')),
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.debt_payments (
  id uuid primary key default extensions.uuid_generate_v4(),
  debt_id uuid references public.debts(id) on delete cascade,
  amount_ngn numeric(15,2) not null,
  payment_date date not null,
  payment_method text,
  notes text,
  created_at timestamptz not null default now()
);

create index idx_debts_entity on public.debts(entity_type, entity_id);
create index idx_debts_status on public.debts(status);
create index idx_debts_due_date on public.debts(due_date);
create index idx_debt_payments_debt on public.debt_payments(debt_id);
