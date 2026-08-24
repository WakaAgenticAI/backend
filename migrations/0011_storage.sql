insert into storage.buckets (id, name, public)
values
  ('reports', 'reports', false),
  ('audio', 'audio', false),
  ('avatars', 'avatars', true)
on conflict (id) do nothing;

create policy "reports_staff_read" on storage.objects
  for select using (
    bucket_id = 'reports' and public.current_role() in ('admin','finance')
  );

create policy "reports_staff_write" on storage.objects
  for insert with check (
    bucket_id = 'reports' and public.current_role() in ('admin','finance')
  );

-- Audio objects are stored as {user_id}/{session_id}/{file}
create policy "audio_select" on storage.objects
  for select using (
    bucket_id = 'audio'
    and (
      auth.uid()::text = (storage.foldername(name))[1]
      or public.current_role() = 'admin'
    )
  );

create policy "audio_insert" on storage.objects
  for insert with check (
    bucket_id = 'audio'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "audio_update" on storage.objects
  for update using (
    bucket_id = 'audio' and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "avatars_public_read" on storage.objects
  for select using (bucket_id = 'avatars');

create policy "avatars_owner_write" on storage.objects
  for insert with check (
    bucket_id = 'avatars' and auth.uid()::text = (storage.foldername(name))[1]
  );
