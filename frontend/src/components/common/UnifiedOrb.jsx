import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Send, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import AgentTrace from "../agents/AgentTrace.jsx";
import { useOrb } from "../../context/OrbContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { appendEventToList, streamAgent } from "../../lib/orbStream.js";
import { useIsMobile } from "../../lib/useMediaQuery.js";

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


export default function UnifiedOrb({ dockedHidden = false } = {}) {
  const { t, isDark } = useTheme();
  const location = useLocation();
  const orb = useOrb();
  const isMobile = useIsMobile();
  const isHome = location.pathname === "/";
  const [open, setOpen] = useState(false);            // desktop: floating panel visible
  const [mobileExpanded, setMobileExpanded] = useState(false);  // mobile non-home: bottom sheet visible
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

  // Drive a streamed orb call. `path` is /orb/chat or /orb/run-agent.
  // `userMessage` is what shows in the conversation as the user bubble.
  // `requestBody` is the JSON sent to the backend.
  const runStream = useCallback(async (path, userMessage, requestBody) => {
    if (running) return;
    const startTs = performance.now();
    setError(null);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
      { role: "trace", events: [], running: true, durationMs: null },
    ]);
    setRunning(true);

    const pushEvent = (evt) => {
      setMessages((prev) => {
        const next = prev.slice();
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "trace") {
            next[i] = { ...next[i], events: appendEventToList(next[i].events, evt) };
            break;
          }
        }
        return next;
      });
    };

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const evt of streamAgent(path, requestBody, controller.signal)) {
        if (evt.event === "done") break;
        if (evt.event === "final_message") {
          setMessages((prev) => [...prev, { role: "answer", data: evt.data }]);
        }
        pushEvent(evt);
      }
    } catch (e) {
      if (e?.name !== "AbortError") setError(String(e?.message || e));
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
  }, [running]);

  const submit = useCallback(async (override) => {
    const text = (typeof override === "string" ? override : input).trim();
    if (!text || running) return;
    setInput("");
    const pageContext = { module: pathToModule(location.pathname), current_item: null };
    await runStream("/orb/chat", text, { message: text, page_context: pageContext });
  }, [input, running, location.pathname, runStream]);

  // Consume pending instructions from the OrbContext — module pages call
  // useOrb().runAgent(...) or .openWithPrompt(...) or .openPanel().
  useEffect(() => {
    if (!orb?.pending) return;
    const p = orb.pending;
    orb.consume();
    // Desktop = floating panel; mobile non-home = bottom sheet; mobile
    // home = already full-page so no panel state to flip.
    if (!isMobile) setOpen(true);
    else if (!isHome) setMobileExpanded(true);
    if (p.mode === "open") {
      // Just open the panel; user will type a question themselves.
      return;
    }
    if (p.mode === "chat") {
      const ctx = { module: pathToModule(location.pathname), current_item: null, ...(p.page_context || {}) };
      runStream("/orb/chat", p.message, { message: p.message, page_context: ctx });
    } else if (p.mode === "run-agent") {
      const ctx = { module: pathToModule(location.pathname), current_item: null, ...(p.page_context || {}) };
      const userMessage = p.message || `Run the ${p.agent} agent`;
      runStream("/orb/run-agent", userMessage, {
        agent: p.agent,
        inputs: p.inputs || {},
        message: p.message || "",
        page_context: ctx,
      });
    }
  }, [orb?.pending, orb, runStream, location.pathname, isMobile, isHome]);

  // Stop any in-flight stream if the orb closes.
  useEffect(() => {
    if (!open && abortRef.current) {
      abortRef.current.abort();
    }
  }, [open]);

  const panelBg = isDark ? "rgba(14,16,36,0.97)" : "rgba(255,255,255,0.98)";
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
      ? `0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px ${t.borderBright}`
      : `0 8px 40px rgba(0,0,0,0.12), 0 0 0 1px ${t.border}`,
    overflow: "hidden",
    transformOrigin: "bottom right",
    animation: closing ? "uo-fadeOut .18s ease forwards" : "uo-fadeIn .22s cubic-bezier(0.34,1.56,0.64,1) forwards",
  };

  // ---- Reusable panel pieces ----------------------------------------------
  const renderHeader = (onClose) => (
    <div style={{
      padding: "12px 14px 10px",
      borderBottom: `1px solid ${t.border}`,
      display: "flex",
      alignItems: "center",
      gap: 10,
      flexShrink: 0,
    }}>
      <img
        src="/reapit-ai-logo.svg"
        alt="Reapit AI"
        style={{
          height: 30,
          width: "auto",
          filter: isDark ? "brightness(0) invert(1)" : "none",
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, fontSize: 12, color: t.textMuted, lineHeight: 1.35 }}>
        AppMarket co-pilot — ask anything.
      </div>
      {onClose && (
        <button onClick={onClose} style={iconBtn(t)} title="Close" aria-label="Close">
          <X size={16} />
        </button>
      )}
    </div>
  );

  const renderBody = () => (
    <div ref={scrollRef} style={{
      flex: 1,
      overflowY: "auto",
      padding: "12px 14px",
      display: "flex",
      flexDirection: "column",
      gap: 10,
      minHeight: 0,
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
  );

  // Mobile input — pill style that matches the docked bar so the
  // homepage / bottom sheet / docked bar all read as the same surface.
  const renderMobileInput = ({ autoFocus = false } = {}) => (
    <div style={{
      padding: "8px 12px calc(8px + env(safe-area-inset-bottom, 0px))",
      background: t.surface,
      borderTop: `1px solid ${t.border}`,
      flexShrink: 0,
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "4px 4px 4px 14px",
        background: isDark ? "rgba(0,0,0,0.25)" : "rgba(0,0,0,0.03)",
        border: `1px solid ${t.border}`,
        borderRadius: 999,
      }}>
        <input
          autoFocus={autoFocus}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Ask Rai…"
          disabled={running}
          style={{
            flex: 1,
            minWidth: 0,
            padding: "10px 0",
            background: "transparent",
            border: "none",
            color: t.text,
            fontSize: 14,
            fontFamily: "inherit",
            outline: "none",
          }}
        />
        <button
          onClick={submit}
          disabled={running}
          aria-label="Send"
          title="Send"
          style={{
            width: 32, height: 32, borderRadius: "50%",
            // Always solid indigo + white icon so the homepage / sheet
            // matches the docked bar exactly. Submit() short-circuits on
            // empty input so the button is safe to tap when empty.
            background: t.accent,
            color: "#fff",
            opacity: running ? 0.55 : 1,
            border: "none",
            cursor: running ? "wait" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
            transition: "opacity .15s",
          }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );

  const renderInput = ({ autoFocus = true } = {}) => (
    <div style={{
      padding: "10px 12px",
      borderTop: `1px solid ${t.border}`,
      display: "flex",
      gap: 8,
      background: t.surface,
      flexShrink: 0,
    }}>
      <input
        autoFocus={autoFocus}
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
  );

  // ---- Mode branches -------------------------------------------------------

  // Mobile + home: Rai fills the body below MobileNav. No internal header
  // chrome — the top nav already brands the page with the active RAI logo.
  // No docked bar, no sheet. Parent <main> constrains the height.
  if (isMobile && isHome) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", background: t.surface }}>
        {renderBody()}
        {renderMobileInput({ autoFocus: false })}
      </div>
    );
  }

  // Mobile + non-home: docked input bar at the bottom; optional bottom sheet.
  if (isMobile) {
    return (
      <>
        <DockedRaiBar
          t={t}
          isDark={isDark}
          hidden={dockedHidden}
          onExpand={() => setMobileExpanded(true)}
        />
        {mobileExpanded && (
          <MobileBottomSheet
            t={t}
            onClose={() => setMobileExpanded(false)}
          >
            {renderHeader(() => setMobileExpanded(false))}
            {renderBody()}
            {renderMobileInput({ autoFocus: true })}
          </MobileBottomSheet>
        )}
      </>
    );
  }

  // Desktop (default): floating panel + the PlasmaOrb visual.
  return (
    <div style={{ position: "fixed", bottom: 16, right: 16, zIndex: 9999, fontFamily: "'Inter', system-ui, sans-serif" }}>
      {open && (
        <div style={panelStyle}>
          {renderHeader(close)}
          {renderBody()}
          {renderInput({ autoFocus: true })}
        </div>
      )}

      {/* Orb visual (always rendered; pointer-events only on the invisible
          button beneath it so the orb itself doesn't block clicks). */}
      <div style={{ position: "relative", width: 56, height: 56, animation: "uo-float 4s ease-in-out infinite" }}>
        <button
          onClick={() => (open ? close() : setOpen(true))}
          aria-label="Open Rai — AppMarket co-pilot"
          title="Rai — AppMarket co-pilot"
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

// Slim input bar pinned to the bottom of the viewport on mobile non-home
// routes. Tapping anywhere opens the bottom sheet so the user gets the
// full chat experience with the keyboard. Auto-hides on scroll-down,
// revealing on scroll-up — `hidden` is driven from MobileShell.
function DockedRaiBar({ t, isDark, onExpand, hidden }) {
  return (
    <div
      role="button"
      onClick={onExpand}
      aria-label="Open Rai"
      aria-hidden={hidden ? "true" : undefined}
      style={{
        position: "fixed",
        left: 8, right: 8,
        bottom: "calc(8px + env(safe-area-inset-bottom, 0px))",
        zIndex: 90,
        background: isDark ? "rgba(14,16,36,0.97)" : "rgba(255,255,255,0.98)",
        border: `1px solid ${t.border}`,
        borderRadius: 999,
        padding: "8px 10px 8px 14px",
        boxShadow: isDark
          ? "0 4px 20px rgba(0,0,0,0.55)"
          : "0 4px 20px rgba(15,18,38,0.10)",
        display: "flex",
        alignItems: "center",
        gap: 10,
        backdropFilter: "blur(12px)",
        cursor: "pointer",
        transform: hidden ? "translateY(140%)" : "translateY(0)",
        opacity: hidden ? 0 : 1,
        pointerEvents: hidden ? "none" : "auto",
        transition: "transform .22s cubic-bezier(0.4,0,0.2,1), opacity .22s",
      }}
    >
      <img
        src="/reapit-ai-logo.svg"
        alt="Reapit AI"
        style={{
          height: 18,
          width: "auto",
          filter: isDark ? "brightness(0) invert(1)" : "none",
          flexShrink: 0,
          pointerEvents: "none",
        }}
      />
      <span style={{ flex: 1, fontSize: 13, color: t.textMuted }}>
        Ask Rai…
      </span>
      <span style={{
        width: 32, height: 32, borderRadius: "50%",
        background: t.accent,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#fff",
        flexShrink: 0,
      }}>
        <Send size={14} />
      </span>
    </div>
  );
}

// Bottom sheet that slides up to 90% viewport height over the module page.
// Backdrop dims + click-outside dismisses. Drag-to-close is Phase B polish.
function MobileBottomSheet({ t, onClose, children }) {
  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 110,
          background: "rgba(15,18,38,0.42)",
          backdropFilter: "blur(2px)",
          animation: "uo-fadeIn .18s ease forwards",
        }}
      />
      <div style={{
        position: "fixed",
        left: 0, right: 0, bottom: 0,
        zIndex: 111,
        height: "90dvh",
        background: t.surface,
        borderTopLeftRadius: 18,
        borderTopRightRadius: 18,
        boxShadow: "0 -8px 32px rgba(15,18,38,0.18)",
        display: "flex",
        flexDirection: "column",
        animation: "uo-sheetIn .22s cubic-bezier(0.4,0,0.2,1) forwards",
        paddingBottom: "env(safe-area-inset-bottom, 0px)",
        overflow: "hidden",
      }}>
        {/* Drag handle */}
        <div style={{
          height: 18,
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}>
          <span style={{
            width: 38, height: 4, borderRadius: 2,
            background: t.border,
          }} />
        </div>
        {children}
      </div>
      <style>{`
        @keyframes uo-sheetIn {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
      `}</style>
    </>
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

function pathToModule(path) {
  if (path === "/" || !path) return "dashboard";
  return path.slice(1).split("/")[0];
}

// Theme-aware components for ReactMarkdown so the rendered answer matches
// the orb's Reapit slate/teal palette. `remark-gfm` is applied at the call-site
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
