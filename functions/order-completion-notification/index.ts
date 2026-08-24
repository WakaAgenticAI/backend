import { errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { serviceClient } from "../_shared/supabase.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();
  if (req.method !== "POST") return errorResponse("Method not allowed", 405);

  const payload = await req.json().catch(() => ({}));
  const record = payload.record ?? payload.new ?? payload;
  const admin = serviceClient();

  const orderId = record.id as string | undefined;
  const status = record.status as string | undefined;
  if (!orderId) return jsonResponse({ skipped: true, reason: "no order id" });

  await admin.from("audit_logs").insert({
    action: `order.${status ?? "updated"}`,
    resource: `orders:${orderId}`,
  });

  const webhook = Deno.env.get("ORDER_WEBHOOK_URL");
  if (webhook) {
    await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event: "order.updated",
        order_id: orderId,
        status,
        total: record.total,
        customer_id: record.customer_id,
      }),
    }).catch(() => undefined);
  }

  return jsonResponse({ ok: true, order_id: orderId, status });
});
