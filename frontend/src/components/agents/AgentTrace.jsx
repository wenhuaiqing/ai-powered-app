import { AlertCircle, Brain, CheckCircle2, Loader2 } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";
import AgentBadge from "./AgentBadge.jsx";
import ToolCallCard from "./ToolCallCard.jsx";

// Render the streamed SSE event timeline. Each event in `events` is
// {event, data, ts?}. The newest event is at the bottom of the list.
export default function AgentTrace({ events, running }) {
  const { t } = useTheme();
  if (!events.length && !running) return null;

  // Collapse per-node status: hide `node_start` if a matching `node_end`
  // exists later in the stream. Each node renders as either a spinner
  // (in-flight) or a tick (done), never both.
  const renderEvents = events.filter((e, i) => {
    if (e.event !== "node_start") return true;
    return !events.slice(i + 1).some(
      (later) => later.event === "node_end" && later.data?.name === e.data?.name
    );
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {renderEvents.map((e, i) => renderEvent(e, i, t))}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }`}</style>
    </div>
  );
}

function renderEvent(e, i, t) {
  const { event, data } = e;
  switch (event) {
    case "planner_decision":
      return <PlannerCard key={i} data={data} t={t} />;
    case "node_start":
      return <NodeStartCard key={i} data={data} t={t} />;
    case "tool_call": {
      const r = e.toolResultPreview;
      return (
        <div key={i} style={{ paddingLeft: 8, marginLeft: 4, borderLeft: `2px solid ${t.border}` }}>
          <ToolCallCard node={data.node} tool={data.tool} args={data.args} preview={r} />
        </div>
      );
    }
    case "tool_result":
      // Already merged into the preceding tool_call card by useOrbStream
      return null;
    case "node_end":
      return <NodeEndCard key={i} data={data} t={t} />;
    case "node_error":
      return <NodeErrorCard key={i} data={data} t={t} />;
    case "final_message":
      // The final answer is rendered separately as an AnswerCard outside
      // the trace, so we skip the duplicate inside the Steps block.
      return null;
    default:
      return null;
  }
}

function PlannerCard({ data, t }) {
  const calls = data?.agents_to_call || [];
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 10,
      padding: "10px 12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <Brain size={14} color={t.accent} />
        <AgentBadge name="planner" />
        <span style={{ fontSize: 12, color: t.textMuted }}>
          routing to {calls.length} agent{calls.length === 1 ? "" : "s"}
        </span>
      </div>
      <div style={{ fontSize: 12, color: t.text, lineHeight: 1.5 }}>
        {data?.reasoning}
      </div>
      {calls.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {calls.map((c, k) => <AgentBadge key={k} name={c.name} />)}
        </div>
      )}
    </div>
  );
}

function NodeStartCard({ data, t }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "2px 4px" }}>
      <Loader2 size={12} color={t.textMuted} className="spin" />
      <AgentBadge name={data.name} />
      <span style={{ fontSize: 12, color: t.textMuted }}>started</span>
    </div>
  );
}

function NodeEndCard({ data, t }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "2px 4px" }}>
      <CheckCircle2 size={12} color={t.accent2} />
      <AgentBadge name={data.name} />
      <span style={{ fontSize: 12, color: t.textMuted }}>complete</span>
    </div>
  );
}

function NodeErrorCard({ data, t }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 8,
      padding: "8px 10px",
      background: t.dotGlow.red,
      border: `1px solid ${t.dot.red}`,
      borderRadius: 8,
      fontSize: 12,
    }}>
      <AlertCircle size={14} color={t.dot.red} style={{ flexShrink: 0, marginTop: 2 }} />
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
          <AgentBadge name={data.name} variant="error" />
          <span style={{ fontWeight: 600, color: t.dot.red }}>error</span>
        </div>
        <div style={{ color: t.text }}>{data.error}</div>
      </div>
    </div>
  );
}

function FinalMessageCard({ data, t }) {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
      border: `1px solid ${t.borderBright}`,
      borderRadius: 10,
      padding: "12px 14px",
      marginTop: 4,
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                    textTransform: "uppercase", color: t.accent, marginBottom: 6 }}>
        Answer
      </div>
      <div style={{ fontSize: 13, color: t.text, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
        {data.message}
      </div>
      {data.used_agents?.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {data.used_agents.map((a, i) => <AgentBadge key={i} name={a} />)}
        </div>
      )}
    </div>
  );
}
