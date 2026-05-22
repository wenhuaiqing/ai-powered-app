import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Send, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import AgentTrace from "../agents/AgentTrace.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { API_BASE_URL } from "../../config.js";

const PlasmaOrb = lazy(() => import("./PlasmaOrb.jsx"));

const STYLE_ID = "unified-orb-keyframes";
function ensureKeyframes() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    @keyframes uo-fadeIn  { from { opacity: 0; transform: scale(0.92); transform-origin: bottom right; }
                             to   { opacity: 1; transform: scale(1);    transform-origin: bottom right; } }
    @keyframes uo-fadeOut { from { opacity: 1; transform: scale(1);    transform-origin: bottom right; }
                             to   { opacity: 0; transform: scale(0.92); transform-origin: bottom right; } }
    @keyframes uo-float   { 0%,100% { transform: translate(0,0); }
                             25% { transform: translate(0.5px,-1px); }
                             50% { transform: translate(-0.3px,-0.5px); }
                             75% { transform: translate(-0.7px,-1.2px); } }
  `;
  document.head.appendChild(style);
}

const SAMPLE_PROMPTS = [
  "What stamp duty applies to a $900k purchase in NSW?",
  "Find me family-friendly 3-bed suburbs under $1.5M within 20km of CBD",
  "Estimate the value of a 4-bed house in Manly with 800sqm",
  "What's happening in the Sydney property market this week?",
];


export default function UnifiedOrb() {
  const { t, isDark } = useTheme();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [closing, setClosing] = useState(false);
  const [input, setInput] = useState("");
  // messages is the full conversation: alternating
  //   {role:"user", content}
  //   {role:"trace", events, durationMs?, running}
  //   {role:"answer", data}
  // Each user prompt produces all three. The trace stays in the history.
  const [messages, setMessages] = useState([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => { ensureKeyframes(); }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, running]);

  const close = useCallback(() => {
    setClosing(true);
    setTimeout(() => { setOpen(false); setClosing(false); }, 180);
  }, []);

  const submit = useCallback(async (override) => {
    const text = (typeof override === "string" ? override : input).trim();
    if (!text || running) return;
    const startTs = performance.now();
    setInput("");
    setError(null);
    // Push user + an empty trace placeholder for this turn.
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "trace", events: [], running: true, durationMs: null },
    ]);
    setRunning(true);

    // Mutate ONLY the last trace message as new events stream in.
    const pushEvent = (evt) => {
      setMessages((prev) => {
        const next = prev.slice();
        // Find the last trace message — it's always the tail trace.
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "trace") {
            next[i] = { ...next[i], events: appendEventToList(next[i].events, evt) };
            break;
          }
        }
        return next;
      });
    };

    const pageContext = {
      module: pathToModule(location.pathname),
      current_item: null,
    };

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${API_BASE_URL}/orb/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: JSON.stringify({ message: text, page_context: pageContext }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        const detail = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${detail.slice(0, 200)}`);
      }
      for await (const evt of readSseStream(res.body, controller.signal)) {
        if (evt.event === "done") break;
        if (evt.event === "final_message") {
          setMessages((prev) => [...prev, { role: "answer", data: evt.data }]);
        }
        pushEvent(evt);
      }
    } catch (e) {
      if (e?.name !== "AbortError") {
        setError(String(e?.message || e));
      }
    } finally {
      const durationMs = performance.now() - startTs;
      setMessages((prev) => {
        const next = prev.slice();
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "trace") {
            next[i] = { ...next[i], running: false, durationMs };
            break;
          }
        }
        return next;
      });
      setRunning(false);
      abortRef.current = null;
    }
  }, [input, running, location.pathname]);

  // Stop any in-flight stream if the orb closes.
  useEffect(() => {
    if (!open && abortRef.current) {
      abortRef.current.abort();
    }
  }, [open]);

  const panelBg = isDark ? "rgba(13,10,28,0.97)" : "rgba(255,255,255,0.98)";
  const panelStyle = {
    position: "absolute",
    bottom: 92,
    right: 0,
    width: 460,
    maxHeight: 620,
    display: "flex",
    flexDirection: "column",
    background: panelBg,
    border: `1px solid ${t.border}`,
    borderRadius: 16,
    backdropFilter: "blur(16px)",
    boxShadow: isDark
      ? "0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(91,45,140,0.22)"
      : "0 8px 40px rgba(0,0,0,0.12), 0 0 0 1px rgba(91,45,140,0.10)",
    overflow: "hidden",
    transformOrigin: "bottom right",
    animation: closing ? "uo-fadeOut .18s ease forwards" : "uo-fadeIn .22s cubic-bezier(0.34,1.56,0.64,1) forwards",
  };

  return (
    <div style={{ position: "fixed", bottom: 16, right: 16, zIndex: 9999, fontFamily: "'Inter', system-ui, sans-serif" }}>
      {open && (
        <div style={panelStyle}>
          {/* Header */}
          <div style={{
            padding: "12px 14px 10px",
            borderBottom: `1px solid ${t.border}`,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}>
            <div style={{
              width: 26, height: 26, borderRadius: 7,
              background: `linear-gradient(135deg, ${t.accent} 0%, ${t.accent2} 100%)`,
            }} />
            <div style={{ flex: 1, lineHeight: 1.1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: t.text }}>AppMarket co-pilot</div>
              <div style={{ fontSize: 11, color: t.textMuted, marginTop: 2 }}>
                Ask anything — agents route automatically.
              </div>
            </div>
            <button onClick={close} style={iconBtn(t)} title="Close">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div ref={scrollRef} style={{
            flex: 1,
            overflowY: "auto",
            padding: "12px 14px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}>
            {messages.length === 0 && !running && (
              <SamplePrompts onPick={(p) => submit(p)} t={t} />
            )}
            {messages.map((m, i) => (
              <MessageRow key={i} message={m} t={t} />
            ))}
            {error && (
              <div style={{
                padding: "8px 10px", fontSize: 12,
                background: t.dotGlow.red, color: t.dot.red,
                border: `1px solid ${t.dot.red}`, borderRadius: 8,
              }}>{error}</div>
            )}
          </div>

          {/* Input */}
          <div style={{
            padding: "10px 12px",
            borderTop: `1px solid ${t.border}`,
            display: "flex",
            gap: 8,
            background: t.surface,
          }}>
            <input
              autoFocus
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="Ask about properties, regulations, or the market..."
              disabled={running}
              style={{
                flex: 1,
                padding: "9px 12px",
                background: isDark ? "rgba(0,0,0,0.25)" : "rgba(0,0,0,0.03)",
                border: `1px solid ${t.border}`,
                borderRadius: 10,
                color: t.text,
                fontSize: 13,
                fontFamily: "inherit",
                outline: "none",
              }}
              onFocus={(e) => (e.target.style.borderColor = t.accent)}
              onBlur={(e) => (e.target.style.borderColor = t.border)}
            />
            <button
              onClick={submit}
              disabled={running || !input.trim()}
              style={{
                padding: "9px 14px",
                background: !input.trim() || running ? t.accentGlow : t.accent,
                color: !input.trim() || running ? t.textMuted : "#fff",
                border: "none",
                borderRadius: 10,
                fontSize: 13,
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: !input.trim() || running ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                transition: "all .15s ease",
              }}
            >
              <Send size={13} />
              {running ? "..." : "Send"}
            </button>
          </div>
        </div>
      )}

      {/* Orb visual (always rendered; pointer-events only on the invisible
          button beneath it so the orb itself doesn't block clicks). */}
      <div style={{ position: "relative", width: 56, height: 56, animation: "uo-float 4s ease-in-out infinite" }}>
        <button
          onClick={() => (open ? close() : setOpen(true))}
          aria-label="Open AppMarket co-pilot"
          title="AppMarket co-pilot"
          style={{
            width: 56, height: 56,
            border: "none",
            background: "transparent",
            cursor: "pointer",
            padding: 0,
            position: "relative",
            transform: open ? "scale(0.92)" : "scale(1)",
            transition: "transform .2s ease",
          }}
        />
      </div>
      <Suspense fallback={null}>
        <PlasmaOrb size={56} isDark={isDark} style={{ pointerEvents: "none", animation: "uo-float 4s ease-in-out infinite" }} />
      </Suspense>
    </div>
  );
}

function MessageRow({ message, t }) {
  if (message.role === "user") {
    return (
      <div style={{ alignSelf: "flex-end", maxWidth: "85%", flexShrink: 0 }}>
        <div style={{
          background: t.accentGlow,
          color: t.text,
          padding: "8px 12px",
          borderRadius: 12,
          border: `1px solid ${t.border}`,
          fontSize: 13,
          lineHeight: 1.45,
          whiteSpace: "pre-wrap",
        }}>
          {message.content}
        </div>
      </div>
    );
  }
  if (message.role === "trace") {
    return <TraceBlock trace={message} t={t} />;
  }
  return <AnswerCard data={message.data} t={t} />;
}

function TraceBlock({ trace, t }) {
  const [open, setOpen] = useState(true);
  const events = trace.events || [];
  const planner = events.find((e) => e.event === "planner_decision");
  const agentCount = planner?.data?.agents_to_call?.length ?? 0;
  const seconds = trace.durationMs != null ? (trace.durationMs / 1000).toFixed(1) : null;

  return (
    <div style={{
      border: `1px solid ${t.border}`,
      borderRadius: 10,
      background: t.surface,
      overflow: "hidden",
      flexShrink: 0,
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          color: t.textMuted,
          fontFamily: "inherit",
          fontSize: 12,
          textAlign: "left",
        }}
      >
        <span style={{
          display: "inline-block",
          width: 0, height: 0,
          borderLeft: `4px solid ${t.textMuted}`,
          borderTop: "4px solid transparent",
          borderBottom: "4px solid transparent",
          transition: "transform .15s ease",
          transform: open ? "rotate(90deg)" : "rotate(0deg)",
        }} />
        <span style={{ fontWeight: 600, color: t.text }}>Steps</span>
        <span>·</span>
        {agentCount > 0 ? (
          <span>{agentCount} agent{agentCount === 1 ? "" : "s"}</span>
        ) : (
          <span>{trace.running ? "planning…" : "no agents"}</span>
        )}
        {seconds && <><span>·</span><span>{seconds}s</span></>}
        {trace.running && agentCount > 0 && (
          <>
            <span>·</span>
            <span style={{ color: t.accent }}>working…</span>
          </>
        )}
      </button>
      {open && (
        <div style={{ padding: "0 12px 10px" }}>
          <AgentTrace events={events} running={trace.running} />
        </div>
      )}
    </div>
  );
}

function AnswerCard({ data, t }) {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
      border: `1px solid ${t.borderBright}`,
      borderRadius: 12,
      padding: "12px 14px",
      flexShrink: 0,
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                    textTransform: "uppercase", color: t.accent, marginBottom: 6 }}>
        Answer
      </div>
      <div style={{ fontSize: 13, color: t.text, lineHeight: 1.6, wordBreak: "break-word" }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents(t)}>
          {data.message || ""}
        </ReactMarkdown>
      </div>
      {Array.isArray(data.used_agents) && data.used_agents.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {data.used_agents.map((a, i) => (
            <span key={i} style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
              textTransform: "uppercase",
              padding: "2px 7px", borderRadius: 4,
              background: t.accent2Glow, color: t.accent2,
            }}>{a}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function SamplePrompts({ onPick, t }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontSize: 11, color: t.textMuted, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
        Try
      </div>
      {SAMPLE_PROMPTS.map((p, i) => (
        <button
          key={i}
          onClick={() => onPick(p)}
          style={{
            textAlign: "left",
            padding: "8px 10px",
            background: t.surface,
            border: `1px dashed ${t.border}`,
            borderRadius: 8,
            color: t.text,
            fontSize: 12,
            fontFamily: "inherit",
            cursor: "pointer",
            transition: "background .15s, border-color .15s",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = t.accent; e.currentTarget.style.background = t.rowHover; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.background = t.surface; }}
        >
          {p}
        </button>
      ))}
    </div>
  );
}

function iconBtn(t) {
  return {
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: 4,
    color: t.textMuted,
    display: "flex",
    alignItems: "center",
    borderRadius: 6,
  };
}

function appendEventToList(list, evt) {
  // Merge tool_result into the most recent matching tool_call so the trace
  // shows one card per tool call with the result preview attached.
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
    return [...list, evt]; // no matching tool_call seen — keep it raw
  }
  return [...list, evt];
}

async function* readSseStream(stream, signal) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    if (signal?.aborted) return;
    const { value, done } = await reader.read();
    if (done) {
      // Flush any trailing event without a final separator.
      const trailing = buffer.trim();
      if (trailing) {
        const evt = parseSseEvent(trailing);
        if (evt) yield evt;
      }
      return;
    }
    // sse-starlette uses \r\n per spec; some intermediaries strip CRs.
    // Normalise to \n then look for the blank-line separator.
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
    if (line.startsWith(":")) continue; // SSE comment / keep-alive ping
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  const dataRaw = dataLines.join("\n");
  if (!dataRaw && event === "message") return null;
  let data;
  try { data = dataRaw ? JSON.parse(dataRaw) : null; } catch { data = dataRaw; }
  return { event, data };
}

function pathToModule(path) {
  if (path === "/" || !path) return "dashboard";
  return path.slice(1).split("/")[0];
}

// Theme-aware components for ReactMarkdown so the rendered answer matches
// the orb's purple/teal palette. `remark-gfm` is applied at the call-site
// to autolink bare URLs and support strikethrough / tables.
function markdownComponents(t) {
  return {
    p:      (props) => <p {...props} style={{ margin: "0 0 8px" }} />,
    ul:     (props) => <ul {...props} style={{ margin: "0 0 8px", paddingLeft: 18 }} />,
    ol:     (props) => <ol {...props} style={{ margin: "0 0 8px", paddingLeft: 18 }} />,
    li:     (props) => <li {...props} style={{ marginBottom: 2 }} />,
    strong: (props) => <strong {...props} style={{ fontWeight: 600, color: t.text }} />,
    em:     (props) => <em {...props} style={{ fontStyle: "italic" }} />,
    a:      (props) => (
      <a
        {...props}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: t.accent, textDecoration: "underline", wordBreak: "break-all" }}
      />
    ),
    code:   (props) => (
      <code
        {...props}
        style={{
          background: t.labelColBg,
          padding: "1px 5px",
          borderRadius: 4,
          fontSize: 12,
          fontFamily: "ui-monospace, Menlo, monospace",
        }}
      />
    ),
    h1: (props) => <h3 {...props} style={{ margin: "8px 0 6px", fontSize: 15, fontWeight: 600 }} />,
    h2: (props) => <h3 {...props} style={{ margin: "8px 0 6px", fontSize: 14, fontWeight: 600 }} />,
    h3: (props) => <h3 {...props} style={{ margin: "8px 0 4px", fontSize: 13, fontWeight: 600 }} />,
  };
}
