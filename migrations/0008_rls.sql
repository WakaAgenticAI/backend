-- Helper: get current user's role without recursive RLS issues
create or replace function public.current_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select role from public.profiles where id = auth.uid();
$$;

grant execute on function public.current_role() to authenticated, anon;

alter table public.profiles enable row level security;
alter table public.customers enable row level security;
alter table public.products enable row level security;
alter table public.warehouses enable row level security;
alter table public.inventory enable row level security;
alter table public.orders enable row level security;
alter table public.order_items enable row level security;
alter table public.debts enable row level security;
alter table public.debt_payments enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.support_tickets enable row level security;
alter table public.reports enable row level security;
alter table public.audit_logs enable row level security;
alter table public.forecasts enable row level security;

-- Profiles: users see/edit their own profile; admins see all
create policy "profiles_self_select" on public.profiles
  for select using (id = auth.uid() or public.current_role() = 'admin');
create policy "profiles_self_update" on public.profiles
  for update using (id = auth.uid());
create policy "profiles_admin_update" on public.profiles
  for update using (public.current_role() = 'admin');

-- Customers: sales + admin full access; ops/finance read-only
create policy "customers_select" on public.customers
  for select using (public.current_role() in ('admin','sales','ops','finance'));
create policy "customers_write" on public.customers
  for insert with check (public.current_role() in ('admin','sales'));
create policy "customers_update" on public.customers
  for update using (public.current_role() in ('admin','sales'));
create policy "customers_delete" on public.customers
  for delete using (public.current_role() = 'admin');

-- Products / warehouses: readable by all authenticated staff, writable by admin/ops
create policy "products_select" on public.products
  for select using (auth.role() = 'authenticated');
create policy "products_write" on public.products
  for insert with check (public.current_role() in ('admin','ops'));
create policy "products_update" on public.products
  for update using (public.current_role() in ('admin','ops'));

create policy "warehouses_select" on public.warehouses
  for select using (auth.role() = 'authenticated');
create policy "warehouses_write" on public.warehouses
  for all using (public.current_role() in ('admin','ops'))
  with check (public.current_role() in ('admin','ops'));

-- Inventory: ops + admin manage; everyone reads
create policy "inventory_select" on public.inventory
  for select using (auth.role() = 'authenticated');
create policy "inventory_write" on public.inventory
  for all using (public.current_role() in ('admin','ops'))
  with check (public.current_role() in ('admin','ops'));

-- Orders: sales creates; ops/admin manage; each user can also see orders they created
create policy "orders_select" on public.orders
  for select using (
    public.current_role() in ('admin','sales','ops','finance')
    or created_by = auth.uid()
  );
create policy "orders_insert" on public.orders
  for insert with check (public.current_role() in ('admin','sales'));
create policy "orders_update" on public.orders
  for update using (public.current_role() in ('admin','sales','ops'));

create policy "order_items_select" on public.order_items
  for select using (exists (select 1 from public.orders o where o.id = order_id));
create policy "order_items_write" on public.order_items
  for all using (public.current_role() in ('admin','sales'))
  with check (public.current_role() in ('admin','sales'));

-- Debts: finance + admin manage; sales/ops read-only
create policy "debts_select" on public.debts
  for select using (public.current_role() in ('admin','finance','sales','ops'));
create policy "debts_write" on public.debts
  for insert with check (public.current_role() in ('admin','finance'));
create policy "debts_update" on public.debts
  for update using (public.current_role() in ('admin','finance'));
create policy "debts_delete" on public.debts
  for delete using (public.current_role() = 'admin');

create policy "debt_payments_select" on public.debt_payments
  for select using (public.current_role() in ('admin','finance','sales','ops'));
create policy "debt_payments_write" on public.debt_payments
  for all using (public.current_role() in ('admin','finance'))
  with check (public.current_role() in ('admin','finance'));

-- Chat: users only see their own sessions/messages; service role bypasses via Edge Functions
create policy "chat_sessions_owner" on public.chat_sessions
  for all using (user_id = auth.uid() or public.current_role() = 'admin')
  with check (user_id = auth.uid() or public.current_role() = 'admin');

create policy "chat_messages_owner" on public.chat_messages
  for select using (
    exists (
      select 1 from public.chat_sessions s
      where s.id = session_id
        and (s.user_id = auth.uid() or public.current_role() = 'admin')
    )
  );
create policy "chat_messages_insert" on public.chat_messages
  for insert with check (
    exists (
      select 1 from public.chat_sessions s
      where s.id = session_id and s.user_id = auth.uid()
    )
  );

create policy "tickets_owner_or_staff" on public.support_tickets
  for select using (created_by = auth.uid() or public.current_role() in ('admin','sales'));
create policy "tickets_insert" on public.support_tickets
  for insert with check (created_by = auth.uid());
create policy "tickets_staff_update" on public.support_tickets
  for update using (public.current_role() in ('admin','sales'));

-- Reports & audit logs: admin/finance only
create policy "reports_rw" on public.reports
  for all using (public.current_role() in ('admin','finance'))
  with check (public.current_role() in ('admin','finance'));
create policy "audit_logs_select" on public.audit_logs
  for select using (public.current_role() = 'admin');
create policy "audit_logs_insert" on public.audit_logs
  for insert with check (true);

-- Forecasts: read for staff, write via Edge Function (service role) only
create policy "forecasts_select" on public.forecasts
  for select using (auth.role() = 'authenticated');
