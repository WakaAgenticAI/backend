create table public.customers (
  id uuid primary key default extensions.uuid_generate_v4(),
  owner_id uuid references public.profiles(id),
  email text unique not null,
  name text not null,
  phone text,
  segment text,
  status text default 'active',
  location text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.warehouses (
  id uuid primary key default extensions.uuid_generate_v4(),
  name text unique not null
);

create table public.products (
  id uuid primary key default extensions.uuid_generate_v4(),
  sku text unique not null,
  name text not null,
  unit text,
  price_ngn numeric(15,2) not null default 0,
  tax_rate numeric(5,4) not null default 0,
  created_at timestamptz not null default now()
);

create table public.inventory (
  id uuid primary key default extensions.uuid_generate_v4(),
  product_id uuid references public.products(id) on delete cascade,
  warehouse_id uuid references public.warehouses(id) on delete cascade,
  on_hand numeric(15,2) not null default 0,
  reserved numeric(15,2) not null default 0,
  unique (product_id, warehouse_id)
);

create table public.orders (
  id uuid primary key default extensions.uuid_generate_v4(),
  customer_id uuid references public.customers(id),
  created_by uuid references public.profiles(id),
  channel text default 'web',
  status text not null default 'created' check (status in ('created','confirmed','fulfilled','cancelled')),
  currency text default 'NGN',
  total numeric(15,2) not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.order_items (
  id uuid primary key default extensions.uuid_generate_v4(),
  order_id uuid references public.orders(id) on delete cascade,
  product_id uuid references public.products(id),
  qty integer not null check (qty > 0),
  price numeric(15,2) not null,
  line_total numeric(15,2) generated always as (qty * price) stored
);

create index idx_orders_customer on public.orders(customer_id);
create index idx_orders_created_by on public.orders(created_by);
create index idx_orders_status on public.orders(status);
create index idx_order_items_order on public.order_items(order_id);
create index idx_inventory_product on public.inventory(product_id);
