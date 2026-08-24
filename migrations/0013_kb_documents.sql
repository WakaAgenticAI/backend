create table public.kb_documents (
  id uuid primary key default extensions.uuid_generate_v4(),
  collection text not null default 'general',
  title text,
  content text not null,
  embedding extensions.vector(1536),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index idx_kb_documents_collection on public.kb_documents(collection);

alter table public.kb_documents enable row level security;

create policy "kb_select" on public.kb_documents
  for select using (auth.role() = 'authenticated');
create policy "kb_admin_write" on public.kb_documents
  for all using (public.current_role() = 'admin')
  with check (public.current_role() = 'admin');

create or replace function public.match_documents(
  query_embedding extensions.vector(1536),
  match_count int default 5,
  filter_collection text default 'general'
)
returns table (id uuid, title text, content text, similarity float)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select
    d.id,
    d.title,
    d.content,
    1 - (d.embedding <=> query_embedding) as similarity
  from public.kb_documents d
  where d.collection = filter_collection
    and d.embedding is not null
  order by d.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function public.search_documents(
  query_text text,
  match_count int default 5,
  filter_collection text default 'general'
)
returns table (id uuid, title text, content text)
language sql
stable
security invoker
set search_path = public
as $$
  select d.id, d.title, d.content
  from public.kb_documents d
  where d.collection = filter_collection
    and (
      d.content ilike '%' || query_text || '%'
      or coalesce(d.title, '') ilike '%' || query_text || '%'
    )
  limit match_count;
$$;

grant execute on function public.search_documents(text, integer, text) to authenticated;
