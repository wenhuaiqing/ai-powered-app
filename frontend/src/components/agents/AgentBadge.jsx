import { useTheme } from "../../context/ThemeContext.jsx";

const LABELS = {
  planner:      "Planner",
  compliance:   "Compliance",
  data_query:   "Data Query",
  matcher:      "Matcher",
  valuation:    "Valuation",
  listing:      "Listing",
  lead_triage:  "Lead Triage",
  market_watch: "Market Watch",
  summariser:   "Summariser",
  graph:        "Graph",
};

export default function AgentBadge({ name, variant = "default" }) {
  const { t } = useTheme();
  const label = LABELS[name] || name;
  const color = variant === "error" ? t.dot.red : t.accent2;
  const bg    = variant === "error" ? t.dotGlow.red : t.accent2Glow;
  return (
    <span style={{
      fontSize: 10,
      fontWeight: 700,
      letterSpacing: "0.06em",
      textTransform: "uppercase",
      padding: "2px 7px",
      borderRadius: 4,
      background: bg,
      color,
      whiteSpace: "nowrap",
    }}>{label}</span>
  );
}
