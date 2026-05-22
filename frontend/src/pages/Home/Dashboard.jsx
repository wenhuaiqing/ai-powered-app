import { useEffect, useState } from "react";
import {
  ArrowUpRight, Brain, Calculator, Database, FileText, Globe2, MessageSquare,
  ScaleIcon, Search, Sparkles, UserCheck,
} from "lucide-react";
import { useOrb } from "../../context/OrbContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtInt } from "../../lib/api.js";

const AGENTS = [
  { name: "Compliance",       icon: ScaleIcon,   blurb: "NSW Fair Trading, Residential Tenancies, stamp duty, FIRB, strata. RAG over a curated corpus + Tavily web fallback." },
  { name: "Data Query",       icon: Database,    blurb: "Natural-language analytics over our DuckDB tables: properties, suburbs, listings, leads." },
  { name: "Property Matcher", icon: Search,      blurb: "Composes Data Query + suburb reviews + ML valuation to rank candidate suburbs for a buyer brief." },
  { name: "Valuation",        icon: Calculator,  blurb: "RandomForest price prediction (trained on 11k NSW sales) with per-feature contributions in AUD." },
  { name: "Listing Drafter",  icon: FileText,    blurb: "Generates listing copy from a property's attributes (structured-output LLM)." },
  { name: "Lead Triage",      icon: UserCheck,   blurb: "Summarises a CRM lead, scores intent 1-5, suggests next actions." },
  { name: "Market Watch",     icon: Globe2,      blurb: "Live web search via Tavily for current property-market news and recent regulatory changes." },
];

const SAMPLES = [
  "What stamp duty applies to a $900k purchase in NSW?",
  "Find me family-friendly 3-bed suburbs under $1.5M within 20km of CBD",
  "Estimate the value of a 4-bed house in Manly with 800sqm",
  "What's happening in the Sydney property market this week?",
];

export default function Dashboard() {
  const { t } = useTheme();
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
      {kpis && (
        <section style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 10,
        }}>
          <KpiCard t={t} label="Active listings"  value={fmtInt(kpis.total_listings)}    sub={`${kpis.for_sale} for sale · ${kpis.for_lease} for lease`} />
          <KpiCard t={t} label="Under offer"      value={fmtInt(kpis.under_offer)} />
          <KpiCard t={t} label="Leads"            value={fmtInt(kpis.leads)}             sub={`${kpis.hot_leads} hot`} />
          <KpiCard t={t} label="Avg DOM"          value={`${kpis.avg_days_on_market} d`} />
          <KpiCard t={t} label="Suburbs covered"  value={fmtInt(kpis.suburbs_covered)} />
          <KpiCard t={t} label="Median sale"      value={fmtAud(kpis.median_sale_price, { short: true })} />
        </section>
      )}

      {/* Agents grid */}
      <section>
        <SectionHeader title="The 7 specialist agents" t={t} icon={Brain} />
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
        }}>
          {AGENTS.map((a) => <AgentCard key={a.name} agent={a} t={t} />)}
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
          <div style={{ fontSize: 12, color: t.textMuted, marginTop: 4 }}>
            Click any prompt to open <strong style={{ color: t.text }}>Rai</strong>, the
            co-pilot, and watch the planner route the specialist agents.
          </div>
        </div>
      </section>
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

// Agent cards are "capabilities" — neutral surface, icon avatar, AI badge.
// Hover lifts the border to accent so the card feels interactive even though
// it doesn't navigate anywhere yet.
function AgentCard({ agent, t }) {
  const Icon = agent.icon || Brain;
  return (
    <div
      style={{
        padding: "14px 16px",
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 10,
        display: "flex",
        gap: 12,
        transition: "border-color .15s ease, transform .15s ease",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = t.accent; e.currentTarget.style.transform = "translateY(-1px)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.transform = "translateY(0)"; }}
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
    </div>
  );
}
