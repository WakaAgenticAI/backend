import { errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { groqComplete, GROQ_MODEL } from "../_shared/groq.ts";
import { requireUser } from "../_shared/supabase.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();
  if (req.method !== "POST") return errorResponse("Method not allowed", 405);

  const { supabase, user } = await requireUser(req);
  if (!user) return errorResponse("Unauthorized", 401);

  const body = await req.json().catch(() => ({}));
  const prompt = String(body.prompt ?? "");
  const collection = String(body.collection ?? "general");
  const topK = Number(body.top_k ?? 3);
  const sessionId = body.session_id as string | undefined;
  if (!prompt) return errorResponse("prompt is required");

  const { data: docs, error } = await supabase.rpc("search_documents", {
    query_text: prompt,
    match_count: topK,
    filter_collection: collection,
  });
  if (error) return errorResponse(error.message, 500);

  const context = (docs ?? [])
    .map((d: { title?: string; content?: string }, i: number) => `[${i + 1}] ${d.title ?? "doc"}: ${d.content}`)
    .join("\n\n");

  const text = await groqComplete([
    {
      role: "system",
      content:
        "You are WakaAgent AI. Answer using the retrieved knowledge base context when it is relevant. If the context is empty, say you don't have a matching document and give a short general answer.",
    },
    {
      role: "user",
      content: `Context:\n${context || "(none)"}\n\nQuestion: ${prompt}`,
    },
  ]);

  if (sessionId) {
    await supabase.from("chat_messages").insert({
      session_id: sessionId,
      sender: "agent",
      content: text,
    });
  }

  return jsonResponse({
    content: text,
    text,
    model: GROQ_MODEL,
    session_id: sessionId,
    sources: docs ?? [],
  });
});
