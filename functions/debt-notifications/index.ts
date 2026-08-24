import { errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { serviceClient } from "../_shared/supabase.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();

  const admin = serviceClient();
  await admin.rpc("mark_overdue_debts");

  const today = new Date().toISOString().slice(0, 10);
  const { data: overdue, error } = await admin
    .from("debts")
    .select("id, type, entity_type, entity_id, amount_ngn, due_date, status, description, priority")
    .in("status", ["overdue", "pending", "partial"])
    .lte("due_date", today)
    .order("due_date", { ascending: true })
    .limit(200);

  if (error) return errorResponse(error.message, 500);

  // Email/SMS delivery is configured via project secrets (RESEND_API_KEY, etc.).
  // This function always returns the scan result so it can be invoked on a schedule.
  return jsonResponse({
    scanned_at: new Date().toISOString(),
    count: overdue?.length ?? 0,
    debts: overdue ?? [],
  });
});
