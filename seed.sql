-- Demo catalog for local development. Auth users are created via the dashboard
-- or `supabase auth` / sign-up; the first signup is promoted to admin.

insert into public.warehouses (id, name) values
  ('11111111-1111-1111-1111-111111111111', 'Lagos Main'),
  ('22222222-2222-2222-2222-222222222222', 'Abuja Hub')
on conflict (name) do nothing;

insert into public.products (id, sku, name, unit, price_ngn, tax_rate) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', 'COKE-50CL', 'Coca-Cola 50cl', 'crate', 3200, 0.075),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', 'PEPSI-50CL', 'Pepsi 50cl', 'crate', 3000, 0.075),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', 'INDO-CART', 'Indomie Carton', 'carton', 8500, 0.075),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', 'IPH-15-PRO', 'iPhone 15 Pro', 'unit', 450000, 0.075),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', 'SGS24', 'Samsung Galaxy S24', 'unit', 380000, 0.075),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6', 'AIRPODS-PRO', 'AirPods Pro', 'unit', 145000, 0.075)
on conflict (sku) do nothing;

insert into public.inventory (product_id, warehouse_id, on_hand, reserved) values
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1', '11111111-1111-1111-1111-111111111111', 240, 12),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2', '11111111-1111-1111-1111-111111111111', 180, 8),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3', '11111111-1111-1111-1111-111111111111', 90, 4),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4', '11111111-1111-1111-1111-111111111111', 45, 6),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5', '11111111-1111-1111-1111-111111111111', 8, 2),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6', '11111111-1111-1111-1111-111111111111', 67, 5)
on conflict (product_id, warehouse_id) do nothing;

insert into public.customers (id, email, name, phone, segment, status, location) values
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1', 'adebayo@email.com', 'Adebayo Johnson', '+2348011111111', 'vip', 'active', 'Lagos'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2', 'fatima@email.com', 'Fatima Abdullahi', '+2348022222222', 'regular', 'active', 'Abuja'),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3', 'chinedu@email.com', 'Chinedu Okafor', '+2348033333333', 'new', 'active', 'Enugu')
on conflict (email) do nothing;

insert into public.debts (id, type, entity_type, entity_id, amount_ngn, description, due_date, status, priority) values
  ('cccccccc-cccc-cccc-cccc-ccccccccccc1', 'receivable', 'customer', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1', 450000, 'Invoice INV-1001', current_date + 14, 'pending', 'medium'),
  ('cccccccc-cccc-cccc-cccc-ccccccccccc2', 'receivable', 'customer', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2', 125000, 'Invoice INV-1002', current_date - 40, 'overdue', 'high'),
  ('cccccccc-cccc-cccc-cccc-ccccccccccc3', 'payable', 'supplier', null, 89000, 'Supplier PO-88', current_date + 7, 'pending', 'low')
on conflict (id) do nothing;

-- Local admin (email/password). First profile is promoted to admin by trigger.
-- Password: admin123
insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  confirmation_token, email_change, email_change_token_new, recovery_token
) values (
  '00000000-0000-0000-0000-000000000000',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'authenticated',
  'authenticated',
  'admin@example.com',
  extensions.crypt('admin123', extensions.gen_salt('bf')),
  now(),
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Admin User"}',
  now(),
  now(),
  '',
  '',
  '',
  ''
) on conflict (id) do nothing;

insert into auth.identities (
  id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
) values (
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  '{"sub":"a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11","email":"admin@example.com"}',
  'email',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  now(),
  now(),
  now()
) on conflict (id) do nothing;

insert into public.kb_documents (collection, title, content, metadata) values
  ('general', 'How to place an order', 'Sales staff can place an order from the Orders page. Select a customer, add products, and confirm. Inventory is reserved atomically via the place_order function.', '{"title":"Place order"}'),
  ('general', 'Checking stock', 'Inventory is tracked per warehouse. on_hand is physical stock; reserved is committed to open orders. Available = on_hand - reserved.', '{"title":"Stock"}'),
  ('general', 'Debt tracking', 'Receivables are money customers owe WakaAgent. Payables are money owed to suppliers. Overdue debts are marked daily.', '{"title":"Debts"}');
