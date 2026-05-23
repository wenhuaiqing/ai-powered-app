import { useEffect, useState } from "react";
import {
  ArrowUpRight, Brain, Calculator, Database, FileText, Globe2, MessageSquare,
  ScaleIcon, Search, Sparkles, UserCheck,
} from "lucide-react";
import { useOrb } from "../../context/OrbContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtInt } from "../../lib/api.js";

const AGENTS = [
  { name: "Compliance",       icon: ScaleIcon,   blurb: "NSW Fair Trading, Residential Tenancies, stamp duty, FIRB, strata. RAG over a curated corpus + Tavily web fallback.",
    sample: "What stamp duty applies to a $900k purchase in NSW?" },
  { name: "Data Query",       icon: Database,    blurb: "Natural-language analytics over our DuckDB tables: properties, suburbs, listings, leads.",
    sample: "Top 10 suburbs by median sale price" },
  { name: "Property Matcher", icon: Search,      blurb: "Composes Data Query + suburb reviews + ML valuation to rank candidate suburbs for a buyer brief.",
    sample: "Find me family-friendly 3-bed suburbs under $1.5M within 20km of CBD" },
  { name: "Valuation",        icon: Calculator,  blurb: "RandomForest price prediction (trained on 11k NSW sales) with per-feature contributions in AUD.",
    sample: "Estimate the value of a 4-bed house in Manly with 800sqm" },
  { name: "Listing Drafter",  icon: FileText,    blurb: "Generates listing copy from a property's attributes (structured-output LLM).",
    sample: "Draft a listing for a 3-bed 2-bath house in Bondi with 600sqm" },
  { name: "Lead Triage",      icon: UserCheck,   blurb: "Summarises a CRM lead, scores intent 1-5, suggests next actions.",
    sample: "Triage a sample CRM lead and suggest next actions" },
  { name: "Market Watch",     icon: Globe2,      blurb: "Live web search via Tavily for current property-market news and recent regulatory changes.",
    sample: "What's happening in the Sydney property market this week?" },
];

const SAMPLES = [
  "What stamp duty applies to a $900k purchase in NSW?",
  "Find me family-friendly 3-bed suburbs under $1.5M within 20km of CBD",
  "Estimate the value of a 4-bed house in Manly with 800sqm",
  "What's happening in the Sydney property market this week?",
];

export default function Dashboard() {
  const { t, isDark } = useTheme();
  const orb = useOrb();
  const [kpis, setKpis] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api("/api/dashboard/kpis")
      .then((d) => { if (!cancelled) setKpis(d); })
      .catch(() => { /* dashboard is best-effort; ignore */ });
    return () => { cancelled = true; };
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      {/* Hero */}
      <div style={{
        padding: "26px 28px",
        background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
        border: `1px solid ${t.border}`,
        borderRadius: 14,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
          <Sparkles size={18} color={t.accent} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
                          textTransform: "uppercase", color: t.accent }}>
            Reapit One-Platform demo
          </span>
        </div>
        <h1 style={{ margin: "0 0 8px", fontSize: 24, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
          Run your entire estate agency on a single platform.
        </h1>
        <p style={{ margin: 0, fontSize: 14, color: t.textMuted, lineHeight: 1.6, maxWidth: 720 }}>
          Mock of Reapit's AI-powered estate agency stack — multi-agent LangGraph
          orchestration, RAG over NSW regulations, text-to-DuckDB, live web search
          via Tavily, and a RandomForest valuation model. Say hi to
          <strong style={{ color: t.text }}> Rai</strong>, the co-pilot bottom-right.
        </p>
      </div>

      {/* KPIs */}
      <section style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
        gap: 10,
      }}>
        {kpis ? (
          <>
            <KpiCard t={t} label="Active listings"  value={fmtInt(kpis.total_listings)}    sub={`${kpis.for_sale} for sale · ${kpis.for_lease} for lease`} />
            <KpiCard t={t} label="Under offer"      value={fmtInt(kpis.under_offer)} />
            <KpiCard t={t} label="Leads"            value={fmtInt(kpis.leads)}             sub={`${kpis.hot_leads} hot`} />
            <KpiCard t={t} label="Avg DOM"          value={`${kpis.avg_days_on_market} d`} />
            <KpiCard t={t} label="Suburbs covered"  value={fmtInt(kpis.suburbs_covered)} />
            <KpiCard t={t} label="Median sale"      value={fmtAud(kpis.median_sale_price, { short: true })} />
          </>
        ) : (
          Array.from({ length: 6 }).map((_, i) => <KpiSkeleton key={i} t={t} index={i} />)
        )}
      </section>

      {/* Agents grid */}
      <section>
        <SectionHeader title="The 7 specialist agents" t={t} icon={Brain} />
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
        }}>
          {AGENTS.map((a) => (
            <AgentCard
              key={a.name}
              agent={a}
              t={t}
              onClick={() => orb.openWithPrompt(a.sample, { module: "dashboard" })}
            />
          ))}
        </div>
      </section>

      {/* Sample prompts */}
      <section>
        <SectionHeader title="Try a prompt" t={t} icon={MessageSquare} />
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 720 }}>
          {SAMPLES.map((s, i) => (
            <SamplePromptButton
              key={i}
              t={t}
              prompt={s}
              onClick={() => orb.openWithPrompt(s, { module: "dashboard" })}
            />
          ))}
          <SweepLine t={t} isDark={isDark} onClick={() => orb.openPanel()} />
          <style>{`
            @keyframes rai-char-sweep {
              0%, 12%, 30%, 100% {
                color: ${t.textMuted};
                text-shadow: none;
              }
              17%, 24% {
                color: #D1263D;
                /* Multi-direction zero-blur text-shadow simulates bold
                   without changing font-weight, so per-char animation
                   doesn't cause layout shift / line re-wrap. */
                text-shadow:
                  0.4px 0 0 currentColor,
                  -0.4px 0 0 currentColor,
                  0 0.4px 0 currentColor,
                  0 -0.4px 0 currentColor;
              }
            }
            /* Heartbeat pulse on the inline RAI logo — two quick zooms
               (lub-dub) then a longer rest, looping forever. The brief
               wobble signals "click me" without competing with the text
               sweep. */
            @keyframes rai-logo-heartbeat {
              0%, 100%       { transform: scale(1); }
              6%             { transform: scale(1.20); }
              12%            { transform: scale(1); }
              18%            { transform: scale(1.12); }
              24%, 70%       { transform: scale(1); }
            }
          `}</style>
        </div>
      </section>
    </div>
  );
}

// Per-character animation: each letter cycles through the rai-char-sweep
// keyframes with a small staggered animation-delay, so the brief red +
// bold-look "highlight" travels left-to-right across the line. The inline
// RAI logo sits between the two text halves and stays static.
const HINT_BEFORE = "Click any prompt to open ";
const HINT_AFTER  = ", the co-pilot, and watch the planner route the specialist agents.";
const HINT_CHAR_DELAY_S = 0.04;
const HINT_CYCLE_S = 5;

function SweepLine({ t, isDark, onClick }) {
  return (
    <button
      onClick={onClick}
      aria-label="Open Rai, the co-pilot"
      style={{
        appearance: "none",
        background: "transparent",
        border: "none",
        padding: "6px 8px",
        marginLeft: -8,
        marginTop: 4,
        borderRadius: 8,
        textAlign: "left",
        font: "inherit",
        fontSize: 12,
        color: t.textMuted,
        lineHeight: 1.6,
        cursor: "pointer",
        transition: "background .15s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = t.accentGlow)}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      onFocus={(e) => (e.currentTarget.style.background = t.accentGlow)}
      onBlur={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {HINT_BEFORE.split("").map((c, i) => (
        <Char key={`b${i}`} ch={c} index={i} />
      ))}
      <img
        src="/reapit-ai-logo.svg"
        alt="Reapit AI"
        style={{
          height: 22,
          width: "auto",
          verticalAlign: "-6px",
          margin: "0 4px",
          filter: isDark ? "brightness(0) invert(1)" : "none",
          pointerEvents: "none",
          display: "inline-block",
          transformOrigin: "center center",
          animation: "rai-logo-heartbeat 3.6s ease-in-out infinite",
        }}
      />
      {HINT_AFTER.split("").map((c, i) => (
        <Char key={`a${i}`} ch={c} index={i + HINT_BEFORE.length + 1} />
      ))}
    </button>
  );
}

function Char({ ch, index }) {
  return (
    <span style={{
      animation: `rai-char-sweep ${HINT_CYCLE_S}s linear infinite`,
      animationDelay: `${index * HINT_CHAR_DELAY_S}s`,
    }}>{ch}</span>
  );
}


// Ghost KPI card shown while /api/dashboard/kpis is in flight. Mirrors
// the KpiCard frame (indigo-tint, 3px left rule, same padding) so the
// transition to real data doesn't shift the layout.
function KpiSkeleton({ t, index = 0 }) {
  return (
    <div style={{
      position: "relative",
      padding: "14px 14px 14px 18px",
      background: t.accentGlow,
      border: `1px solid ${t.border}`,
      borderRadius: 10,
      overflow: "hidden",
      opacity: 0.55 - index * 0.04,
    }}>
      <div style={{
        position: "absolute",
        left: 0, top: 0, bottom: 0,
        width: 3,
        background: t.accent,
        opacity: 0.5,
      }} />
      <div style={{
        height: 8, width: "60%",
        background: t.borderBright,
        borderRadius: 4,
        marginBottom: 10,
        opacity: 0.6,
      }} />
      <div style={{
        height: 18, width: "45%",
        background: t.borderBright,
        borderRadius: 4,
      }} />
    </div>
  );
}

function SamplePromptButton({ t, prompt, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px 10px 16px",
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 10,
        fontSize: 13,
        color: t.text,
        fontFamily: "inherit",
        cursor: "pointer",
        textAlign: "left",
        transition: "background .15s, border-color .15s, transform .12s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = t.accentGlow;
        e.currentTarget.style.borderColor = t.accent;
        e.currentTarget.style.transform = "translateX(2px)";
        const arrow = e.currentTarget.querySelector("[data-arrow]");
        if (arrow) arrow.style.color = t.accent;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = t.surface;
        e.currentTarget.style.borderColor = t.border;
        e.currentTarget.style.transform = "translateX(0)";
        const arrow = e.currentTarget.querySelector("[data-arrow]");
        if (arrow) arrow.style.color = t.textMuted;
      }}
    >
      <MessageSquare size={13} color={t.accent2} style={{ flexShrink: 0 }} />
      <span style={{ flex: 1 }}>{prompt}</span>
      <ArrowUpRight size={14} data-arrow style={{ color: t.textMuted, flexShrink: 0, transition: "color .15s" }} />
    </button>
  );
}

function SectionHeader({ title, t, icon: Icon }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
      {Icon && <Icon size={15} color={t.accent} />}
      <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: t.text, letterSpacing: "-0.005em" }}>
        {title}
      </h2>
    </div>
  );
}

// KPI cards are "live state" — indigo-tinted, bold accent numbers, left-rule
// stripe. Visually distinct from the neutral white "capability" agent cards.
function KpiCard({ t, label, value, sub }) {
  return (
    <div style={{
      position: "relative",
      padding: "14px 14px 14px 18px",
      background: t.accentGlow,
      border: `1px solid ${t.border}`,
      borderRadius: 10,
      overflow: "hidden",
    }}>
      <div style={{
        position: "absolute",
        left: 0, top: 0, bottom: 0,
        width: 3,
        background: t.accent,
      }} />
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
                    textTransform: "uppercase", color: t.accent, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 700, color: t.text, letterSpacing: "-0.02em", lineHeight: 1 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11, color: t.textMuted, marginTop: 5 }}>{sub}</div>}
    </div>
  );
}

// Agent cards are "capabilities" — neutral surface, icon avatar, AI badge,
// and clicking fires a sample prompt at Rai so the user can see the agent
// in action. Hover lifts the border to indigo and reveals an arrow chip
// to telegraph "try this".
function AgentCard({ agent, t, onClick }) {
  const Icon = agent.icon || Brain;
  return (
    <button
      onClick={onClick}
      aria-label={`Try ${agent.name}: ${agent.sample}`}
      title={`Try: "${agent.sample}"`}
      style={{
        position: "relative",
        padding: "14px 16px",
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 10,
        display: "flex",
        gap: 12,
        textAlign: "left",
        font: "inherit",
        cursor: "pointer",
        transition: "border-color .15s ease, transform .15s ease, box-shadow .15s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = t.accent;
        e.currentTarget.style.transform = "translateY(-1px)";
        e.currentTarget.style.boxShadow = `0 6px 18px ${t.accentGlow}`;
        const arrow = e.currentTarget.querySelector("[data-arrow]");
        if (arrow) { arrow.style.opacity = 1; arrow.style.transform = "translateX(0)"; }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = t.border;
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "none";
        const arrow = e.currentTarget.querySelector("[data-arrow]");
        if (arrow) { arrow.style.opacity = 0; arrow.style.transform = "translateX(-4px)"; }
      }}
    >
      <div style={{
        width: 36, height: 36, borderRadius: 9,
        background: t.accent2Glow,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: t.accent2,
        flexShrink: 0,
      }}>
        <Icon size={17} strokeWidth={1.8} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: t.text }}>{agent.name}</span>
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: "0.08em",
            padding: "1px 5px", borderRadius: 3, lineHeight: "12px",
            background: t.accent2Glow, color: t.accent2,
          }}>AI</span>
        </div>
        <div style={{ fontSize: 12, color: t.textMuted, lineHeight: 1.55 }}>
          {agent.blurb}
        </div>
      </div>
      <ArrowUpRight
        size={14}
        data-arrow
        style={{
          position: "absolute",
          top: 12, right: 12,
          color: t.accent,
          opacity: 0,
          transform: "translateX(-4px)",
          transition: "opacity .15s, transform .15s",
        }}
      />
    </button>
  );
}
