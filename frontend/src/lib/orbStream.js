// Shared SSE consumer used by the orb panel and the agent buttons.
// Reads /orb/chat or /orb/run-agent and yields typed events.

import { API_BASE_URL } from "../config.js";

// Scale-to-zero hosting can bounce a request during scale transitions
// (the ingress briefly has no endpoint and no armed activator). Retry
// the initial POST a couple of times before giving up; steady-state
// cold starts are held by the platform itself, so the spinner covers
// the wait either way.
const RETRY_DELAYS_MS = [4000, 8000];

export async function* streamAgent(path, body, signal) {
  let res;
  for (let attempt = 0; ; attempt++) {
    try {
      res = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify(body),
        signal,
      });
    } catch (e) {
      if (e?.name === "AbortError" || attempt >= RETRY_DELAYS_MS.length) throw e;
      await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
      continue;
    }
    if (res.ok && res.body) break;
    if (attempt >= RETRY_DELAYS_MS.length || signal?.aborted) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`);
    }
    await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
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
