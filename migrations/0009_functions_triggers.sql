create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trg_profiles_updated before update on public.profiles
  for each row execute function public.set_updated_at();
create trigger trg_customers_updated before update on public.customers
  for each row execute function public.set_updated_at();
create trigger trg_orders_updated before update on public.orders
  for each row execute function public.set_updated_at();
create trigger trg_debts_updated before update on public.debts
  for each row execute function public.set_updated_at();

create or replace function public.mark_overdue_debts()
returns void
language sql
security definer
set search_path = public
as $$
  update public.debts
    set status = 'overdue'
    where status in ('pending','partial') and due_date < current_date;
$$;

create or replace function public.log_audit()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.audit_logs (user_id, action, resource)
  values (auth.uid(), tg_op, tg_table_name);
  return coalesce(new, old);
end;
$$;

create trigger trg_audit_debts
  after insert or update or delete on public.debts
  for each row execute function public.log_audit();

create trigger trg_audit_orders
  after insert or update or delete on public.orders
  for each row execute function public.log_audit();
