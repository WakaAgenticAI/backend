import { createClient, type SupabaseClient } from "jsr:@supabase/supabase-js@2";

export function userClient(req: Request): SupabaseClient {
  const authHeader = req.headers.get("Authorization") ?? "";
  return createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_ANON_KEY")!,
    { global: { headers: { Authorization: authHeader } } },
  );
}

export function serviceClient(): SupabaseClient {
  return createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );
}

export async function requireUser(req: Request) {
  const supabase = userClient(req);
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    return { supabase, user: null as null };
  }
  return { supabase, user: data.user };
}
