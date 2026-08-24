import { corsHeaders, errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { groqChat, groqComplete, GROQ_MODEL } from "../_shared/groq.ts";
import { requireUser } from "../_shared/supabase.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();
  if (req.method !== "POST") return errorResponse("Method not allowed", 405);

  const { supabase, user } = await requireUser(req);
  if (!user) return errorResponse("Unauthorized", 401);

  const body = await req.json().catch(() => ({}));
  const prompt = String(body.prompt ?? body.message ?? "");
  const sessionId = body.session_id as string | undefined;
  const language = String(body.language ?? "en");
  const stream = Boolean(body.stream);
  const mode = String(body.mode ?? "complete");
  const temperature = Number(body.temperature ?? 0.7);
  const maxTokens = Number(body.max_tokens ?? 800);

  if (!prompt) return errorResponse("prompt is required");

  if (mode === "classify") {
    const raw = await groqComplete(
      [
        {
          role: "system",
          content:
            'Classify the user message for a Nigerian distribution-management assistant. Reply with JSON only: {"intent":"orders.create|inventory.check|support.open|debts.list|chat.general","confidence":0-1,"agent":"orders|inventory|support|finance|orchestrator"}',
        },
        { role: "user", content: prompt },
      ],
      { temperature: 0, max_tokens: 200 },
    );
    try {
      const parsed = JSON.parse(raw.replace(/```json|```/g, "").trim());
      return jsonResponse({
        intent: parsed.intent ?? "chat.general",
        confidence: Number(parsed.confidence ?? 0.5),
        agent: parsed.agent ?? "orchestrator",
      });
    } catch {
      return jsonResponse({ intent: "chat.general", confidence: 0.4, agent: "orchestrator" });
    }
  }

  const system = `You are WakaAgent AI, an assistant for Nigerian FMCG / electronics distribution. Be concise and practical. Prefer NGN amounts. Language: ${language}.`;

  if (sessionId) {
    await supabase.from("chat_messages").insert({
      session_id: sessionId,
      sender: "user",
      content: prompt,
    });
  }

  if (stream) {
    const groqResp = await groqChat({
      messages: [
        { role: "system", content: system },
        { role: "user", content: prompt },
      ],
      temperature,
      max_tokens: maxTokens,
      stream: true,
    });

    const encoder = new TextEncoder();
    let full = "";
    const readable = new ReadableStream({
      async start(controller) {
        const reader = groqResp.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }
        const decoder = new TextDecoder();
        let buffer = "";
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";
            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;
              const data = line.slice(6).trim();
              if (data === "[DONE]") continue;
              try {
                const parsed = JSON.parse(data);
                const chunk = parsed.choices?.[0]?.delta?.content ?? "";
                if (chunk) {
                  full += chunk;
                  controller.enqueue(encoder.encode(`data: ${JSON.stringify({ content: chunk })}\n\n`));
                }
              } catch {
                // ignore malformed SSE
              }
            }
          }
          controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        } finally {
          if (sessionId && full) {
            await supabase.from("chat_messages").insert({
              session_id: sessionId,
              sender: "agent",
              content: full,
            });
          }
          controller.close();
        }
      },
    });

    return new Response(readable, {
      headers: {
        ...corsHeaders,
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  }

  const text = await groqComplete(
    [
      { role: "system", content: system },
      { role: "user", content: prompt },
    ],
    { temperature, max_tokens: maxTokens },
  );

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
  });
});
