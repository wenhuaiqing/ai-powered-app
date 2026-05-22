// Properties module — Sales + Lettings unified list with a row-click drawer.
// The drawer has three agent buttons that fire /orb/run-agent via useOrb().

import { useEffect, useMemo, useState } from "react";
import { BedDouble, Bath, Calculator, CarFront, FileText, MapPin, ScaleIcon, Sparkles } from "lucide-react";
import Drawer from "../../components/common/Drawer.jsx";
import { useOrb } from "../../context/OrbContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtDate, fmtInt } from "../../lib/api.js";

const FILTERS = [
  { key: "all",      label: "All" },
  { key: "For Sale", label: "For sale" },
  { key: "For Lease",label: "For lease" },
];

export default function Properties() {
  const { t } = useTheme();
  const orb = useOrb();
  const [filter, setFilter] = useState("all");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api(`/api/properties/list?status=${encodeURIComponent(filter)}&limit=60`)
      .then((data) => { if (!cancelled) setItems(data.items || []); })
      .catch((e)   => { if (!cancelled) setError(String(e?.message || e)); })
      .finally(()  => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filter]);

  const selected = useMemo(
    () => items.find((i) => i.listing_id === selectedId) || null,
    [items, selectedId],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Header t={t} count={items.length} />

      <div style={{ display: "flex", gap: 8 }}>
        {FILTERS.map((f) => (
          <FilterChip key={f.key} t={t} active={filter === f.key} onClick={() => setFilter(f.key)}>
            {f.label}
          </FilterChip>
        ))}
      </div>

      {loading && <Skeleton t={t} />}
      {error && <ErrorBox t={t}>{error}</ErrorBox>}
      {!loading && !error && (
        <Table items={items} t={t} onRowClick={(id) => setSelectedId(id)} />
      )}

      <Drawer
        open={!!selected}
        onClose={() => setSelectedId(null)}
        title={selected ? `${selected.suburb} ${selected.type?.toLowerCase() || ""}` : ""}
        subtitle={selected
          ? `${selected.num_bed} bed · ${selected.num_bath} bath · ${selected.property_size} sqm · ${fmtInt(selected.km_from_cbd)} km from CBD`
          : ""}
      >
        {selected && <PropertyDetail item={selected} t={t} orb={orb} />}
      </Drawer>
    </div>
  );
}


function Header({ t, count }) {
  return (
    <div>
      <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
        Properties
      </h1>
      <p style={{ margin: 0, fontSize: 13, color: t.textMuted }}>
        {fmtInt(count)} synthetic listing{count === 1 ? "" : "s"} backed by the Domain Sydney sales data. Click a row to open the agent toolkit.
      </p>
    </div>
  );
}

function FilterChip({ t, active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 14px",
        borderRadius: 999,
        border: `1px solid ${active ? t.accent : t.border}`,
        background: active ? t.accentGlow : t.surface,
        color: active ? t.accent : t.text,
        fontSize: 12,
        fontWeight: 600,
        fontFamily: "inherit",
        cursor: "pointer",
        transition: "all .15s ease",
      }}
    >{children}</button>
  );
}

function Skeleton({ t }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} style={{
          height: 48,
          background: t.surface,
          border: `1px solid ${t.border}`,
          borderRadius: 8,
          opacity: 0.6 - i * 0.05,
        }} />
      ))}
    </div>
  );
}

function ErrorBox({ t, children }) {
  return (
    <div style={{
      padding: "10px 12px",
      background: t.dotGlow.red,
      color: t.dot.red,
      border: `1px solid ${t.dot.red}`,
      borderRadius: 8,
      fontSize: 13,
    }}>{children}</div>
  );
}

const stageColors = (t) => ({
  "New":         t.accent2,
  "Listed":      t.accent,
  "Under Offer": t.dot.yellow,
  "Sold":        t.textMuted,
});

function Table({ items, t, onRowClick }) {
  const stageColor = stageColors(t);
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 12,
      overflow: "hidden",
    }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: "1.2fr 0.5fr 0.6fr 0.6fr 0.8fr 0.7fr 1fr",
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
        <div>Suburb</div>
        <div>Type</div>
        <div>Bed/Bath</div>
        <div>Size</div>
        <div>Price</div>
        <div>DOM</div>
        <div>Stage / Agent</div>
      </div>
      {items.length === 0 && (
        <div style={{ padding: "16px 14px", color: t.textMuted, fontSize: 13 }}>
          No properties match this filter.
        </div>
      )}
      {items.map((it) => (
        <button
          key={it.listing_id}
          onClick={() => onRowClick(it.listing_id)}
          style={{
            display: "grid",
            gridTemplateColumns: "1.2fr 0.5fr 0.6fr 0.6fr 0.8fr 0.7fr 1fr",
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
            <span style={{ fontWeight: 600 }}>{it.suburb}</span>
            <span style={{ fontSize: 11, color: t.textMuted }}>{it.region || "—"}</span>
          </div>
          <div style={{ fontSize: 12, color: t.textMuted }}>{it.type || "—"}</div>
          <div style={{ fontSize: 12 }}>{it.num_bed}b · {it.num_bath}ba</div>
          <div style={{ fontSize: 12 }}>{it.property_size ? `${it.property_size} sqm` : "—"}</div>
          <div style={{ fontWeight: 600 }}>{fmtAud(it.asking_price, { short: true })}</div>
          <div style={{ fontSize: 12, color: t.textMuted }}>{it.days_on_market} d</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
              padding: "2px 6px", borderRadius: 4,
              background: t.bg, color: stageColor[it.stage] || t.textMuted,
              border: `1px solid ${stageColor[it.stage] || t.border}`,
            }}>{it.stage}</span>
            <span style={{ color: t.textMuted }}>{it.agent_name}</span>
          </div>
        </button>
      ))}
    </div>
  );
}


function PropertyDetail({ item, t, orb }) {
  const valuationInputs = {
    num_bed: item.num_bed,
    num_bath: item.num_bath,
    num_parking: item.num_parking,
    property_size: item.property_size,
    suburb: item.suburb,
    type: item.type,
  };
  const pageContext = {
    module: "properties",
    current_item: {
      listing_id: item.listing_id,
      address: `${item.suburb} ${item.type || "property"}`,
      ...valuationInputs,
      asking_price: item.asking_price,
      km_from_cbd: item.km_from_cbd,
      region: item.region,
    },
  };

  const runValuation = () => orb.runAgent(
    "valuation",
    valuationInputs,
    pageContext,
    `Estimate the value of ${item.num_bed}-bed ${item.type?.toLowerCase() || "property"} in ${item.suburb}.`,
  );
  const runListing = () => orb.runAgent(
    "listing",
    valuationInputs,
    pageContext,
    `Draft listing copy for the ${item.suburb} ${item.type?.toLowerCase() || "property"}.`,
  );
  const runCompliance = () => orb.runAgent(
    "compliance",
    { query: `What disclosure and cooling-off obligations apply to selling a residential property in NSW like the ${item.stage?.toLowerCase()} listing in ${item.suburb}?` },
    pageContext,
    `Compliance check for the ${item.suburb} listing.`,
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* Hero block */}
      <div style={{
        padding: "16px 18px",
        background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
        border: `1px solid ${t.border}`,
        borderRadius: 12,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                      textTransform: "uppercase", color: t.accent, marginBottom: 4 }}>
          {item.status}
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, color: t.text }}>
          {fmtAud(item.asking_price)}
        </div>
        <div style={{ fontSize: 13, color: t.textMuted, marginTop: 4 }}>
          Listed {fmtDate(item.listed_date)} · {item.days_on_market} days on market · {item.agent_name}
        </div>
      </div>

      {/* Spec grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 8,
      }}>
        <Spec t={t} icon={BedDouble} label="Bed"      value={item.num_bed} />
        <Spec t={t} icon={Bath}      label="Bath"     value={item.num_bath} />
        <Spec t={t} icon={CarFront}  label="Parking"  value={item.num_parking} />
        <Spec t={t} icon={MapPin}    label="km / CBD" value={fmtInt(item.km_from_cbd)} />
      </div>

      <Field t={t} label="Property type" value={item.type} />
      <Field t={t} label="Land size"     value={item.property_size ? `${item.property_size} sqm` : "—"} />
      <Field t={t} label="Region"        value={item.region || "—"} />
      <Field t={t} label="Suburb median (2021)"
             value={fmtAud(item.median_house_price_2021)} />
      <Field t={t} label="Family-friendliness"
             value={item.family_friendliness != null ? `${item.family_friendliness}/10` : "—"} />
      <Field t={t} label="Safety"
             value={item.safety != null ? `${item.safety}/10` : "—"} />

      {/* Agent toolkit */}
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
          <AgentBtn t={t} icon={Calculator} onClick={runValuation}>Estimate value</AgentBtn>
          <AgentBtn t={t} icon={FileText}   onClick={runListing}>Draft listing</AgentBtn>
          <AgentBtn t={t} icon={ScaleIcon}  onClick={runCompliance}>Compliance check</AgentBtn>
        </div>
        <div style={{ fontSize: 11, color: t.textMuted, marginTop: 8 }}>
          Each button routes the property attributes into the matching specialist agent.
          The orb opens with a full SSE trace.
        </div>
      </section>
    </div>
  );
}

function Spec({ t, icon: Icon, label, value }) {
  return (
    <div style={{
      padding: "10px 12px",
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 10,
      display: "flex",
      flexDirection: "column",
      gap: 4,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 4, color: t.textMuted }}>
        <Icon size={12} />
        <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>{label}</span>
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: t.text }}>{value ?? "—"}</div>
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
        transition: "transform .12s ease, box-shadow .12s ease",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-1px)")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
    >
      <Icon size={14} />
      {children}
    </button>
  );
}
