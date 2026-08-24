export const GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions";
export const GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions";
export const GROQ_MODEL = "llama-3.3-70b-versatile";
export const GROQ_WHISPER_MODEL = "whisper-large-v3";

export function groqKey(): string {
  const key = Deno.env.get("GROQ_API_KEY");
  if (!key) throw new Error("GROQ_API_KEY is not set");
  return key;
}

export async function groqChat(body: Record<string, unknown>): Promise<Response> {
  const resp = await fetch(GROQ_CHAT_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${groqKey()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      ...body,
    }),
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`Groq ${resp.status}: ${txt}`);
  }
  return resp;
}

export async function groqComplete(
  messages: Array<{ role: string; content: string }>,
  options: { temperature?: number; max_tokens?: number } = {},
): Promise<string> {
  const resp = await groqChat({
    messages,
    temperature: options.temperature ?? 0.7,
    max_tokens: options.max_tokens ?? 800,
    stream: false,
  });
  const json = await resp.json();
  return json.choices?.[0]?.message?.content ?? "";
}
