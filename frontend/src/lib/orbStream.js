// Shared SSE consumer used by the orb panel and the agent buttons.
// Reads /orb/chat or /orb/run-agent and yields typed events.

import { API_BASE_URL } from "../config.js";

export async function* streamAgent(path, body, signal) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`);
  }
  yield* readSse(res.body, signal);
}

async function* readSse(stream, signal) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    if (signal?.aborted) return;
    const { value, done } = await reader.read();
    if (done) {
      const tail = buffer.trim();
      if (tail) {
        const evt = parseSseEvent(tail);
        if (evt) yield evt;
      }
      return;
    }
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let sepIdx;
    while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sepIdx);
      buffer = buffer.slice(sepIdx + 2);
      const evt = parseSseEvent(raw);
      if (evt) yield evt;
    }
  }
}

function parseSseEvent(raw) {
  let event = "message";
  const dataLines = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  const dataRaw = dataLines.join("\n");
  if (!dataRaw && event === "message") return null;
  let data;
  try { data = dataRaw ? JSON.parse(dataRaw) : null; } catch { data = dataRaw; }
  return { event, data };
}

// Merge tool_result into the most recent matching tool_call so the trace
// shows one card per tool call with the result preview attached.
export function appendEventToList(list, evt) {
  if (evt.event === "tool_result") {
    for (let i = list.length - 1; i >= 0; i--) {
      const p = list[i];
      if (p.event === "tool_call"
          && p.data?.node === evt.data?.node
          && p.data?.tool === evt.data?.tool
          && !p.toolResultPreview) {
        const next = list.slice();
        next[i] = { ...p, toolResultPreview: evt.data.preview };
        return next;
      }
    }
    return [...list, evt];
  }
  return [...list, evt];
}
