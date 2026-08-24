import { errorResponse, jsonResponse, optionsResponse } from "../_shared/cors.ts";
import { GROQ_TRANSCRIBE_URL, GROQ_WHISPER_MODEL, groqKey } from "../_shared/groq.ts";
import { requireUser, serviceClient } from "../_shared/supabase.ts";

function extensionFromFilename(name: string): string {
  const parts = name.split(".");
  return parts.length > 1 ? parts.pop()!.toLowerCase() : "webm";
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return optionsResponse();
  if (req.method !== "POST") return errorResponse("Method not allowed", 405);

  const { supabase, user } = await requireUser(req);
  if (!user) return errorResponse("Unauthorized", 401);

  const body = await req.json().catch(() => ({}));
  const filename = String(body.filename ?? "recording.webm");
  const language = body.language && body.language !== "auto" ? String(body.language) : undefined;
  const sessionId = body.session_id as string | undefined;

  let bytes: Uint8Array | null = null;

  if (typeof body.audio_data === "string" && body.audio_data.length > 0) {
    const bin = atob(body.audio_data);
    bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  } else if (typeof body.audio_url === "string" && body.audio_url.length > 0) {
    const path = body.audio_url.replace(/^audio\//, "");
    const { data, error } = await supabase.storage.from("audio").download(path);
    if (error || !data) return errorResponse(error?.message ?? "Failed to download audio", 400);
    bytes = new Uint8Array(await data.arrayBuffer());
  }

  if (!bytes) return errorResponse("audio_data or audio_url is required");

  const whisperKey = Deno.env.get("WHISPER_API_KEY") || groqKey();
  const form = new FormData();
  form.append("file", new Blob([bytes], { type: "audio/webm" }), filename);
  form.append("model", GROQ_WHISPER_MODEL);
  if (language) form.append("language", language);

  const whisperUrl = Deno.env.get("WHISPER_API_URL") || GROQ_TRANSCRIBE_URL;
  const resp = await fetch(whisperUrl, {
    method: "POST",
    headers: { Authorization: `Bearer ${whisperKey}` },
    body: form,
  });
  if (!resp.ok) {
    const txt = await resp.text();
    return errorResponse(`Transcription failed: ${resp.status} ${txt}`, 502);
  }
  const result = await resp.json();
  const text = result.text ?? result.transcript ?? "";
  const detected = result.language ?? language ?? "en";

  if (sessionId && text) {
    await supabase.from("chat_messages").insert({
      session_id: sessionId,
      sender: "user",
      content: text,
      audio_url: body.audio_url ?? null,
    });
  }

  // Persist original bytes if the client only sent base64
  if (body.audio_data && sessionId) {
    const admin = serviceClient();
    const path = `${user.id}/${sessionId}/${crypto.randomUUID()}.${extensionFromFilename(filename)}`;
    await admin.storage.from("audio").upload(path, bytes, { contentType: "audio/webm", upsert: false });
  }

  return jsonResponse({
    text,
    language: detected,
    confidence: result.confidence ?? null,
  });
});
