import { errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { groqComplete } from "../_shared/groq.ts";
import { requireUser } from "../_shared/supabase.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();
  if (req.method !== "POST") return errorResponse("Method not allowed", 405);

  const { user } = await requireUser(req);
  if (!user) return errorResponse("Unauthorized", 401);

  const body = await req.json().catch(() => ({}));
  const message = String(body.message ?? "");
  const context = String(body.context ?? "customer_service");
  if (!message) return errorResponse("message is required");

  const raw = await groqComplete(
    [
      {
        role: "system",
        content: `You are WakaAgent AI. Detect the language of the user message (en, pcm/Nigerian Pidgin, ha/Hausa, yo/Yoruba, ig/Igbo) and reply in the same language.
Return JSON only:
{"original_message":"...","detected_language":"en|pcm|ha|yo|ig","confidence":0-1,"english_translation":"...","response":"...","response_language":"en|pcm|ha|yo|ig"}
Context: ${context}`,
      },
      { role: "user", content: message },
    ],
    { temperature: 0.4, max_tokens: 800 },
  );

  try {
    const parsed = JSON.parse(raw.replace(/```json|```/g, "").trim());
    return jsonResponse({
      original_message: parsed.original_message ?? message,
      detected_language: parsed.detected_language ?? "en",
      confidence: Number(parsed.confidence ?? 0.5),
      english_translation: parsed.english_translation ?? message,
      response: parsed.response ?? raw,
      response_language: parsed.response_language ?? parsed.detected_language ?? "en",
    });
  } catch {
    return jsonResponse({
      original_message: message,
      detected_language: "en",
      confidence: 0.3,
      english_translation: message,
      response: raw,
      response_language: "en",
    });
  }
});
