import { errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { requireUser, serviceClient } from "../_shared/supabase.ts";

function csvEscape(value: unknown): string {
  const v = value === undefined || value === null ? "" : String(value);
  if (/[",\n]/.test(v)) return `"${v.replace(/"/g, '""')}"`;
  return v;
}

function toCsv(headers: string[], rows: Record<string, unknown>[]): string {
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((h) => csvEscape(row[h])).join(","));
  }
  return lines.join("\n");
}

function periodLabel(kind: string): string {
  const now = new Date();
  if (kind === "monthly-audit") {
    return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
  }
  return now.toISOString().slice(0, 10);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();
  if (req.method !== "POST") return errorResponse("Method not allowed", 405);

  const { user } = await requireUser(req);
  if (!user) return errorResponse("Unauthorized", 401);

  const body = await req.json().catch(() => ({}));
  const kind = String(body.kind ?? "daily-sales");
  const period = String(body.period ?? periodLabel(kind));
  const admin = serviceClient();

  const { data: reportRow, error: insertError } = await admin
    .from("reports")
    .insert({
      kind,
      period,
      status: "processing",
      requested_by: user.id,
    })
    .select()
    .single();

  if (insertError || !reportRow) {
    return errorResponse(insertError?.message ?? "Failed to create report row", 500);
  }

  try {
    const { data: orders, error: ordersError } = await admin
      .from("orders")
      .select("id, customer_id, status, channel, total, currency, created_at, customers(name, email)")
      .order("created_at", { ascending: false })
      .limit(1000);
    if (ordersError) throw ordersError;

    const rows = (orders ?? []).map((o: Record<string, unknown>) => {
      const customer = (o.customers as { name?: string; email?: string } | null) ?? {};
      return {
        id: o.id,
        customer_name: customer.name ?? "",
        customer_email: customer.email ?? "",
        status: o.status,
        channel: o.channel,
        total: o.total,
        currency: o.currency,
        created_at: o.created_at,
      };
    });

    const csv = toCsv(
      ["id", "customer_name", "customer_email", "status", "channel", "total", "currency", "created_at"],
      rows,
    );
    const path = `${kind}/${period}/${reportRow.id}.csv`;
    const { error: uploadError } = await admin.storage
      .from("reports")
      .upload(path, new Blob([csv], { type: "text/csv" }), { upsert: true, contentType: "text/csv" });
    if (uploadError) throw uploadError;

    const { data: updated, error: updateError } = await admin
      .from("reports")
      .update({ status: "ready", file_path: path })
      .eq("id", reportRow.id)
      .select()
      .single();
    if (updateError) throw updateError;

    return jsonResponse(updated);
  } catch (err) {
    await admin.from("reports").update({ status: "failed" }).eq("id", reportRow.id);
    return errorResponse(err instanceof Error ? err.message : String(err), 500);
  }
});
