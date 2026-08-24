create table public.forecasts (
  id uuid primary key default extensions.uuid_generate_v4(),
  product_id uuid references public.products(id),
  forecast jsonb not null,
  reorder_alert boolean default false,
  created_at timestamptz not null default now()
);

create index idx_forecasts_product on public.forecasts(product_id, created_at desc);
