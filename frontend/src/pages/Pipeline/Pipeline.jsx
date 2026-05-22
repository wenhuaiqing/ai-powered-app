// Pipeline (CRM) module — synthetic leads list with a row-click drawer.
// Drawer agent buttons: Triage lead, Match properties.

import { useEffect, useMemo, useState } from "react";
import { Mail, MapPin, Phone, Search, Sparkles, UserCheck } from "lucide-react";
import Drawer from "../../components/common/Drawer.jsx";
import { useOrb } from "../../context/OrbContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtDate } from "../../lib/api.js";

const URGENCY_COLOR = (t, u) => ({
  high:   { fg: t.dot.red,    bg: t.dotGlow.red },
  medium: { fg: t.dot.yellow, bg: t.dotGlow.yellow },
  low:    { fg: t.textMuted,  bg: t.bg },
}[u || "medium"]);

const INTENT_COLOR = (t, intent) => ({
  Buying:               t.accent,
  Renting:              t.accent2,
  "Selling appraisal":  t.dot.yellow,
}[intent] || t.textMuted);


export default function Pipeline() {
  const { t } = useTheme();
  const orb = useOrb();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api("/api/pipeline/leads?limit=50")
      .then((d)  => { if (!cancelled) setItems(d.items || []); })
      .catch((e) => { if (!cancelled) setError(String(e?.message || e)); })
      .finally(()=> { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const selected = useMemo(
    () => items.find((i) => i.lead_id === selectedId) || null,
    [items, selectedId],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Header t={t} count={items.length} />

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ height: 64, background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, opacity: 0.6 - i * 0.05 }} />
          ))}
        </div>
      )}
      {error && (
        <div style={{ padding: "10px 12px", background: t.dotGlow.red, color: t.dot.red, border: `1px solid ${t.dot.red}`, borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}
      {!loading && !error && (
        <LeadTable items={items} t={t} onRowClick={(id) => setSelectedId(id)} />
      )}

      <Drawer
        open={!!selected}
        onClose={() => setSelectedId(null)}
        title={selected ? selected.name : ""}
        subtitle={selected
          ? `${selected.intent} · created ${fmtDate(selected.created_date)}`
          : ""}
      >
        {selected && <LeadDetail item={selected} t={t} orb={orb} />}
      </Drawer>
    </div>
  );
}

function Header({ t, count }) {
  return (
    <div>
      <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
        Pipeline
      </h1>
      <p style={{ margin: 0, fontSize: 13, color: t.textMuted }}>
        {count} synthetic CRM lead{count === 1 ? "" : "s"}. Click a row to triage or auto-match listings.
      </p>
    </div>
  );
}

function LeadTable({ items, t, onRowClick }) {
  return (
    <div style={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12, overflow: "hidden" }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: "1.3fr 1fr 1fr 0.8fr 0.6fr",
        gap: 12,
        padding: "10px 14px",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: t.textMuted,
        background: t.bg,
        borderBottom: `1px solid ${t.border}`,
      }}>
        <div>Lead</div>
        <div>Intent / area</div>
        <div>Budget</div>
        <div>Notes</div>
        <div>Urgency</div>
      </div>
      {items.length === 0 && (
        <div style={{ padding: "16px 14px", color: t.textMuted, fontSize: 13 }}>No leads yet.</div>
      )}
      {items.map((it) => {
        const urg = URGENCY_COLOR(t, it.urgency);
        const intentColor = INTENT_COLOR(t, it.intent);
        return (
          <button
            key={it.lead_id}
            onClick={() => onRowClick(it.lead_id)}
            style={{
              display: "grid",
              gridTemplateColumns: "1.3fr 1fr 1fr 0.8fr 0.6fr",
              gap: 12,
              padding: "11px 14px",
              width: "100%",
              background: "transparent",
              border: "none",
              borderBottom: `1px solid ${t.rowDivider}`,
              color: t.text,
              fontFamily: "inherit",
              fontSize: 13,
              textAlign: "left",
              cursor: "pointer",
              alignItems: "center",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = t.rowHover)}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.3 }}>
              <span style={{ fontWeight: 600 }}>{it.name}</span>
              <span style={{ fontSize: 11, color: t.textMuted }}>{it.email}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.3 }}>
              <span style={{ color: intentColor, fontWeight: 600, fontSize: 12 }}>{it.intent}</span>
              <span style={{ fontSize: 11, color: t.textMuted }}>{it.preferred_suburb} · ≤{it.max_km_from_cbd}km</span>
            </div>
            <div style={{ fontSize: 12 }}>
              {fmtAud(it.budget_min, { short: true })} - {fmtAud(it.budget_max, { short: true })}
            </div>
            <div style={{ fontSize: 11, color: t.textMuted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {it.notes}
            </div>
            <div>
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
                padding: "2px 6px", borderRadius: 4,
                background: urg.bg, color: urg.fg,
                border: `1px solid ${urg.fg}`,
              }}>{it.urgency}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}


function LeadDetail({ item, t, orb }) {
  const pageContext = {
    module: "pipeline",
    current_item: {
      lead_id:           item.lead_id,
      name:              item.name,
      email:             item.email,
      phone:             item.phone,
      intent:            item.intent,
      min_bed:           item.min_bed,
      min_bath:          item.min_bath,
      min_parking:       item.min_parking,
      preferred_suburb:  item.preferred_suburb,
      max_km_from_cbd:   item.max_km_from_cbd,
      budget_min:        item.budget_min,
      budget_max:        item.budget_max,
      urgency:           item.urgency,
      notes:             item.notes,
    },
  };

  const runTriage = () => orb.runAgent(
    "lead_triage",
    { lead: pageContext.current_item },
    pageContext,
    `Triage lead ${item.name} (${item.intent} in ${item.preferred_suburb}).`,
  );
  const runMatcher = () => orb.runAgent(
    "matcher",
    {
      min_bed: item.min_bed,
      max_price: item.budget_max,
      max_km_from_cbd: item.max_km_from_cbd,
      preferred_suburb: item.preferred_suburb,
      lifestyle: item.notes,
    },
    pageContext,
    `Find properties matching ${item.name}'s brief.`,
  );

  const urg = URGENCY_COLOR(t, item.urgency);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* Hero */}
      <div style={{
        padding: "16px 18px",
        background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
        border: `1px solid ${t.border}`,
        borderRadius: 12,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                          textTransform: "uppercase", color: t.accent }}>
            {item.intent}
          </span>
          <span style={{
            fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
            padding: "2px 6px", borderRadius: 4,
            background: urg.bg, color: urg.fg, border: `1px solid ${urg.fg}`,
          }}>{item.urgency} urgency</span>
        </div>
        <div style={{ fontSize: 18, fontWeight: 600, color: t.text }}>
          Budget {fmtAud(item.budget_min)} – {fmtAud(item.budget_max)}
        </div>
        <div style={{ fontSize: 13, color: t.textMuted, marginTop: 4 }}>
          Looking in {item.preferred_suburb}, within {item.max_km_from_cbd} km of CBD.
        </div>
      </div>

      {/* Contact */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <ContactRow t={t} icon={Mail}    label={item.email} />
        <ContactRow t={t} icon={Phone}   label={item.phone} />
        <ContactRow t={t} icon={MapPin}  label={`Prefers ${item.preferred_suburb}`} />
      </div>

      <Field t={t} label="Min beds"     value={item.min_bed} />
      <Field t={t} label="Min baths"    value={item.min_bath} />
      <Field t={t} label="Min parking"  value={item.min_parking} />
      <Field t={t} label="Created"      value={fmtDate(item.created_date)} />

      {/* Notes */}
      <section style={{ padding: "12px 14px", background: t.bg, borderRadius: 10, border: `1px solid ${t.border}` }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                      textTransform: "uppercase", color: t.textMuted, marginBottom: 6 }}>
          Notes
        </div>
        <div style={{ fontSize: 13, color: t.text, lineHeight: 1.55 }}>{item.notes}</div>
      </section>

      {/* Agents */}
      <section style={{
        padding: "14px 16px",
        background: t.surface,
        border: `1px dashed ${t.borderBright}`,
        borderRadius: 12,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Sparkles size={14} color={t.accent2} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                          textTransform: "uppercase", color: t.accent2 }}>
            AppMarket agents
          </span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          <AgentBtn t={t} icon={UserCheck} onClick={runTriage}>Triage lead</AgentBtn>
          <AgentBtn t={t} icon={Search}    onClick={runMatcher}>Match properties</AgentBtn>
        </div>
        <div style={{ fontSize: 11, color: t.textMuted, marginTop: 8 }}>
          Triage scores intent and suggests next actions. Match composes Data Query + reviews RAG + Valuation to rank candidate suburbs.
        </div>
      </section>
    </div>
  );
}

function ContactRow({ t, icon: Icon, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, color: t.textMuted, fontSize: 12 }}>
      <Icon size={13} />
      <span style={{ color: t.text }}>{label}</span>
    </div>
  );
}

function Field({ t, label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline",
                  padding: "6px 0", borderBottom: `1px solid ${t.rowDivider}` }}>
      <span style={{ fontSize: 12, color: t.textMuted }}>{label}</span>
      <span style={{ fontSize: 13, color: t.text, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function AgentBtn({ t, icon: Icon, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "9px 14px",
        background: t.accent,
        color: "#fff",
        border: "none",
        borderRadius: 999,
        fontSize: 13,
        fontWeight: 600,
        fontFamily: "inherit",
        cursor: "pointer",
        transition: "transform .12s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-1px)")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
    >
      <Icon size={14} />
      {children}
    </button>
  );
}
