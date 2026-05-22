import { Brain, MessageSquare, Sparkles } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";

const AGENTS = [
  { name: "Compliance",   blurb: "NSW Fair Trading, Residential Tenancies, stamp duty, FIRB, strata. RAG over a curated corpus + Tavily web fallback." },
  { name: "Data Query",   blurb: "Natural-language analytics over our DuckDB tables: properties, suburbs, listings, leads." },
  { name: "Property Matcher", blurb: "Composes Data Query + suburb reviews + ML valuation to rank candidate suburbs for a buyer brief." },
  { name: "Valuation",    blurb: "RandomForest price prediction (trained on 11k NSW sales) with per-feature contributions in AUD." },
  { name: "Listing Drafter", blurb: "Generates listing copy from a property's attributes (structured-output LLM)." },
  { name: "Lead Triage",  blurb: "Summarises a CRM lead, scores intent 1-5, suggests next actions." },
  { name: "Market Watch", blurb: "Live web search via Tavily for current property-market news and recent regulatory changes." },
];

const SAMPLES = [
  "What stamp duty applies to a $900k purchase in NSW?",
  "Find me family-friendly 3-bed suburbs under $1.5M within 20km of CBD",
  "Estimate the value of a 4-bed house in Manly with 800sqm",
  "What's happening in the Sydney property market this week?",
];

export default function Dashboard() {
  const { t } = useTheme();
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
          via Tavily, and a RandomForest valuation model. Try the AppMarket
          co-pilot bottom-right.
        </p>
      </div>

      {/* Agents grid */}
      <section>
        <SectionHeader title="The 7 specialist agents" t={t} icon={Brain} />
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 12,
        }}>
          {AGENTS.map((a) => (
            <div key={a.name} style={{
              padding: "14px 16px",
              background: t.surface,
              border: `1px solid ${t.border}`,
              borderRadius: 10,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: t.text, marginBottom: 6 }}>
                {a.name}
              </div>
              <div style={{ fontSize: 12, color: t.textMuted, lineHeight: 1.55 }}>
                {a.blurb}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Sample prompts */}
      <section>
        <SectionHeader title="Try a prompt" t={t} icon={MessageSquare} />
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 720 }}>
          {SAMPLES.map((s, i) => (
            <div key={i} style={{
              padding: "10px 14px",
              background: t.surface,
              border: `1px dashed ${t.border}`,
              borderRadius: 10,
              fontSize: 13,
              color: t.text,
            }}>{s}</div>
          ))}
          <div style={{ fontSize: 12, color: t.textMuted, marginTop: 4 }}>
            Open the co-pilot (bottom-right) and paste one to see the planner route the
            specialist agents.
          </div>
        </div>
      </section>
    </div>
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
