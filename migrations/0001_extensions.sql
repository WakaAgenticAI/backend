-- Extensions required by WakaAgent AI (uuid PKs, crypto, RAG embeddings)
create extension if not exists "uuid-ossp" with schema extensions;
create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;
