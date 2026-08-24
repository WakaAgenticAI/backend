create or replace function public.place_order(
  p_customer_id uuid,
  p_items jsonb,
  p_channel text default 'web'
) returns public.orders
language plpgsql
security definer
set search_path = public
as $$
declare
  v_order public.orders;
  v_item jsonb;
  v_price numeric;
  v_total numeric := 0;
  v_role text;
begin
  v_role := public.current_role();
  if v_role is null or v_role not in ('admin', 'sales') then
    raise exception 'not authorized to place orders';
  end if;

  if p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    raise exception 'order must contain at least one item';
  end if;

  insert into public.orders (customer_id, created_by, status, channel)
  values (p_customer_id, auth.uid(), 'created', coalesce(p_channel, 'web'))
  returning * into v_order;

  for v_item in select * from jsonb_array_elements(p_items) loop
    select price_ngn into v_price
      from public.products
      where id = (v_item->>'product_id')::uuid;

    if v_price is null then
      raise exception 'product not found: %', v_item->>'product_id';
    end if;

    insert into public.order_items (order_id, product_id, qty, price)
    values (
      v_order.id,
      (v_item->>'product_id')::uuid,
      (v_item->>'qty')::int,
      v_price
    );

    update public.inventory
      set reserved = reserved + (v_item->>'qty')::int
      where product_id = (v_item->>'product_id')::uuid;

    v_total := v_total + v_price * (v_item->>'qty')::int;
  end loop;

  update public.orders set total = v_total where id = v_order.id returning * into v_order;
  return v_order;
end;
$$;

grant execute on function public.place_order(uuid, jsonb, text) to authenticated;

create or replace view public.debt_aging
with (security_invoker = true)
as
select
  id, entity_type, entity_id, amount_ngn, due_date, status,
  case
    when due_date is null then 'no_due_date'
    when current_date - due_date <= 30 then '0-30'
    when current_date - due_date <= 60 then '31-60'
    when current_date - due_date <= 90 then '61-90'
    else '90+'
  end as aging_bucket
from public.debts
where status in ('pending','partial','overdue');

create or replace function public.debt_aging_report()
returns json
language sql
stable
security invoker
set search_path = public
as $$
  select json_build_object(
    'range_0_30', coalesce(sum(amount_ngn) filter (where aging_bucket = '0-30'), 0),
    'range_31_60', coalesce(sum(amount_ngn) filter (where aging_bucket = '31-60'), 0),
    'range_61_90', coalesce(sum(amount_ngn) filter (where aging_bucket = '61-90'), 0),
    'range_90_plus', coalesce(sum(amount_ngn) filter (where aging_bucket = '90+'), 0),
    'total_overdue_amount', coalesce(sum(amount_ngn) filter (where aging_bucket in ('31-60','61-90','90+')), 0),
    'total_debts', count(*)::int,
    'total_amount', coalesce(sum(amount_ngn), 0)
  )
  from public.debt_aging;
$$;

create or replace function public.debt_summary()
returns json
language sql
stable
security invoker
set search_path = public
as $$
  select json_build_object(
    'receivables_total', coalesce(sum(amount_ngn) filter (where type = 'receivable'), 0),
    'payables_total', coalesce(sum(amount_ngn) filter (where type = 'payable'), 0),
    'receivables_count', count(*) filter (where type = 'receivable'),
    'payables_count', count(*) filter (where type = 'payable'),
    'overdue_receivables', coalesce(sum(amount_ngn) filter (where type = 'receivable' and status = 'overdue'), 0),
    'overdue_payables', coalesce(sum(amount_ngn) filter (where type = 'payable' and status = 'overdue'), 0)
  )
  from public.debts
  where status <> 'cancelled';
$$;

grant execute on function public.debt_aging_report() to authenticated;
grant execute on function public.debt_summary() to authenticated;
grant execute on function public.mark_overdue_debts() to authenticated;
