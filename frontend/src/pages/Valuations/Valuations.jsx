// Valuations module — two tabs:
//   Predictor: form -> /api/valuations/predict -> predicted price + contributions bar
//   Model Explorer: /api/valuations/model-info -> metrics + feature importance + residuals

import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, Cell,
} from "recharts";
import { Calculator, LineChart as LineIcon, Sparkles } from "lucide-react";
import SearchableSelect from "../../components/common/SearchableSelect.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtInt } from "../../lib/api.js";
import { useIsMobile } from "../../lib/useMediaQuery.js";

const DEFAULTS = {
  num_bed: 3,
  num_bath: 2,
  num_parking: 1,
  property_size: 600,
  suburb: "Bondi",
  type: "House",
};

export default function Valuations() {
  const { t } = useTheme();
  const [tab, setTab] = useState("predictor");
  const [info, setInfo] = useState(null);

  // Fetch model metadata once at the top level so both tabs can share it
  // (subtitle range banner here, full metrics + importance + residuals in
  // ModelExplorer).
  useEffect(() => {
    let cancelled = false;
    api("/api/valuations/model-info")
      .then((d) => { if (!cancelled) setInfo(d); })
      .catch(() => { /* page still renders if model-info fails */ });
    return () => { cancelled = true; };
  }, []);

  const range = info?.data_range;
  const metrics = info?.metrics;

  // Subtitle: row count + headline metrics. Year range deliberately omitted
  // here — it's surfaced in the yellow DataRangeBanner below the header.
  const subtitleParts = [];
  if (metrics?.n_train) subtitleParts.push(`${fmtInt(metrics.n_train + (metrics.n_test || 0))} NSW sales`);
  if (metrics?.mae_aud) subtitleParts.push(`MAE ${fmtAud(metrics.mae_aud, { short: true })}`);
  if (metrics?.r2 != null) subtitleParts.push(`R² ${Number(metrics.r2).toFixed(3)}`);
  const subtitle = subtitleParts.length
    ? `RandomForest trained on ${subtitleParts.join(" · ")}.`
    : "RandomForest trained on the bundled NSW sales dataset.";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <header>
        <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
          Valuations
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: t.textMuted }}>{subtitle}</p>
      </header>

      <DataRangeBanner t={t} range={range} />

      <Tabs t={t} value={tab} onChange={setTab} />

      {tab === "predictor"
        ? <Predictor t={t} range={range} />
        : <ModelExplorer t={t} info={info} />}
    </div>
  );
}

function DataRangeBanner({ t, range }) {
  if (!range?.earliest_year) return null;
  const span = range.earliest_year === range.latest_year
    ? `${range.earliest_year}`
    : `${range.earliest_year} – ${range.latest_year}`;
  return (
    <div style={{
      padding: "10px 14px",
      fontSize: 12,
      color: t.textMuted,
      background: t.dotGlow.yellow,
      border: `1px solid ${t.dot.yellow}`,
      borderRadius: 8,
      lineHeight: 1.55,
    }}>
      <strong style={{ color: t.dot.yellow, fontWeight: 700 }}>Data note:</strong>{" "}
      Model trained on Domain sales from <strong style={{ color: t.text }}>{span}</strong>.
      Predicted prices reflect that period and don't account for any market
      movements since.
    </div>
  );
}

function Tabs({ t, value, onChange }) {
  const tabs = [
    { key: "predictor", label: "Predictor",      icon: Calculator },
    { key: "explorer",  label: "Model Explorer", icon: LineIcon },
  ];
  return (
    <div style={{ display: "flex", gap: 4, borderBottom: `1px solid ${t.border}` }}>
      {tabs.map((tb) => {
        const active = value === tb.key;
        const Icon = tb.icon;
        return (
          <button
            key={tb.key}
            onClick={() => onChange(tb.key)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "10px 14px",
              border: "none",
              borderBottom: `2px solid ${active ? t.accent : "transparent"}`,
              background: "transparent",
              color: active ? t.accent : t.textMuted,
              fontWeight: active ? 600 : 500,
              fontSize: 13,
              fontFamily: "inherit",
              cursor: "pointer",
              transition: "color .15s, border-color .15s",
            }}
          >
            <Icon size={14} />
            {tb.label}
          </button>
        );
      })}
    </div>
  );
}


/* ============================== Predictor ============================== */

function Predictor({ t, range }) {
  const isMobile = useIsMobile();
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suburbs, setSuburbs] = useState([]);

  useEffect(() => {
    let cancelled = false;
    api("/api/valuations/suburbs")
      .then((d) => {
        if (cancelled) return;
        // Sort by sales descending so the most-modelled suburbs surface
        // first when the input is empty; alphabetical fallback for ties.
        const sorted = (d.suburbs || []).slice().sort((a, b) => {
          if (b.sales !== a.sales) return b.sales - a.sales;
          return a.name.localeCompare(b.name);
        });
        setSuburbs(sorted.map((s) => ({ value: s.name, label: s.name, hint: `${s.sales} sale${s.sales === 1 ? "" : "s"}` })));
      })
      .catch(() => { /* dropdown silently falls back to no options */ });
    return () => { cancelled = true; };
  }, []);

  const update = (k) => (e) => {
    const raw = e.target.value;
    const next = (k === "suburb" || k === "type") ? raw : Number(raw);
    setForm((f) => ({ ...f, [k]: next }));
  };

  const submit = async (e) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api("/api/valuations/predict", { method: "POST", body: form });
      setResult(data);
    } catch (err) {
      setError(String(err?.message || err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: isMobile ? "1fr" : "minmax(280px, 360px) 1fr",
      gap: 18,
    }}>
      {/* Form */}
      <form
        onSubmit={submit}
        style={{
          padding: "16px 18px",
          background: t.surface,
          border: `1px solid ${t.border}`,
          borderRadius: 12,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          height: "fit-content",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <Sparkles size={14} color={t.accent2} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                          textTransform: "uppercase", color: t.accent2 }}>
            Property attributes
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <NumField t={t} label="Beds"    value={form.num_bed}     onChange={update("num_bed")}     min={0} max={15} />
          <NumField t={t} label="Baths"   value={form.num_bath}    onChange={update("num_bath")}    min={0} max={15} />
          <NumField t={t} label="Parking" value={form.num_parking} onChange={update("num_parking")} min={0} max={10} />
          <NumField t={t} label="Size (sqm)" value={form.property_size} onChange={update("property_size")} min={20} max={20000} step={10} />
        </div>

        <Field t={t} label="Suburb">
          <SearchableSelect
            value={form.suburb}
            onChange={update("suburb")}
            options={suburbs}
            placeholder={suburbs.length ? "Type to search 637 suburbs…" : "Loading…"}
            disabled={suburbs.length === 0}
          />
        </Field>
        <Field t={t} label="Type">
          <select value={form.type} onChange={update("type")} style={inputStyle(t)}>
            <option>House</option>
            <option>Apartment</option>
            <option>Townhouse</option>
            <option>Studio</option>
          </select>
        </Field>

        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: 6,
            padding: "10px 14px",
            background: loading ? t.accentGlow : t.accent,
            color: loading ? t.textMuted : "#fff",
            border: "none",
            borderRadius: 999,
            fontSize: 13,
            fontWeight: 600,
            fontFamily: "inherit",
            cursor: loading ? "not-allowed" : "pointer",
            transition: "background .15s",
          }}
        >
          {loading ? "Predicting…" : "Predict price"}
        </button>
      </form>

      {/* Result */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {error && (
          <div style={{ padding: "10px 12px", background: t.dotGlow.red, color: t.dot.red, border: `1px solid ${t.dot.red}`, borderRadius: 8, fontSize: 13 }}>
            {error}
          </div>
        )}
        {!result && !error && !loading && (
          <EmptyHint t={t} />
        )}
        {result && <ResultBlock t={t} result={result} range={range} />}
      </div>
    </div>
  );
}

function EmptyHint({ t }) {
  return (
    <div style={{
      padding: "26px 22px",
      background: t.surface,
      border: `1px dashed ${t.border}`,
      borderRadius: 12,
      color: t.textMuted,
      fontSize: 13,
      lineHeight: 1.6,
    }}>
      Fill the form and hit Predict. The result panel shows the predicted price, an 80% confidence interval drawn from the
      forest's tree spread, and per-feature contributions in AUD.
    </div>
  );
}

function ResultBlock({ t, result, range }) {
  const ci = result.confidence_interval || [0, 0];
  const span = range?.earliest_year && range?.latest_year
    ? (range.earliest_year === range.latest_year
        ? `${range.earliest_year}`
        : `${range.earliest_year}–${range.latest_year}`)
    : null;
  return (
    <>
      <div style={{
        padding: "18px 22px",
        background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
        border: `1px solid ${t.borderBright}`,
        borderRadius: 12,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                      textTransform: "uppercase", color: t.accent, marginBottom: 6 }}>
          Predicted price
        </div>
        <div style={{ fontSize: 32, fontWeight: 700, color: t.text, letterSpacing: "-0.02em" }}>
          {fmtAud(result.predicted_price)}
        </div>
        <div style={{ fontSize: 12, color: t.textMuted, marginTop: 6 }}>
          80% interval {fmtAud(ci[0])} – {fmtAud(ci[1])}
        </div>
        {span && (
          <div style={{ fontSize: 11, color: t.textMuted, marginTop: 8, fontStyle: "italic" }}>
            Based on {span} sales — not adjusted for market movement since.
          </div>
        )}
      </div>

      <ContributionsChart t={t} contributions={result.contributions || []} />
    </>
  );
}

function ContributionsChart({ t, contributions }) {
  const data = contributions
    .slice()
    .sort((a, b) => Math.abs(b.contribution_aud) - Math.abs(a.contribution_aud))
    .slice(0, 8)
    .map((c) => ({
      name: prettifyFeature(c.feature),
      value: c.contribution_aud,
      raw:   c,
    }));

  if (data.length === 0) {
    return (
      <div style={{ padding: 14, fontSize: 12, color: t.textMuted, background: t.surface, border: `1px solid ${t.border}`, borderRadius: 10 }}>
        No per-feature contributions returned.
      </div>
    );
  }

  return (
    <div style={{ padding: "14px 16px 8px", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                        textTransform: "uppercase", color: t.textMuted }}>
          Per-feature contribution (AUD)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={t.gridDot} strokeDasharray="2 4" />
          <XAxis type="number" tickFormatter={(v) => fmtAud(v, { short: true })} stroke={t.textMuted} fontSize={11} />
          <YAxis type="category" dataKey="name" stroke={t.textMuted} fontSize={11} width={110} />
          <ReferenceLine x={0} stroke={t.border} />
          <Tooltip
            cursor={{ fill: t.rowHover }}
            contentStyle={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 12 }}
            formatter={(v) => fmtAud(v)}
            labelFormatter={(name, items) => {
              const raw = items?.[0]?.payload?.raw;
              return raw?.value != null ? `${name} (${raw.value})` : name;
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.value >= 0 ? t.accent : t.dot.red} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}


/* ============================== Model Explorer ============================== */

function ModelExplorer({ t, info }) {
  // info is fetched at the top-level Valuations component and passed in.
  // While it's null we render placeholders the same shape as the real
  // layout so the page doesn't jump when the data lands.
  const loading = info == null;
  const error = null;

  if (loading) return <ModelExplorerSkeleton t={t} />;
  if (error) return (
    <div style={{ padding: "10px 12px", background: t.dotGlow.red, color: t.dot.red, border: `1px solid ${t.dot.red}`, borderRadius: 8, fontSize: 13 }}>
      {error}
    </div>
  );

  const m  = info?.metrics            || {};
  const fi = (info?.feature_importance || []).slice(0, 12).map((f) => ({
    name: prettifyFeature(f.feature),
    importance: f.importance,
  }));
  const res = info?.residuals || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Metrics grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
        <MetricCard t={t} label="MAE"           value={fmtAud(m.mae_aud)} />
        <MetricCard t={t} label="RMSE"          value={fmtAud(m.rmse_aud)} />
        <MetricCard t={t} label="R²"            value={m.r2 != null ? m.r2.toFixed(3) : "—"} />
        <MetricCard t={t} label="Train rows"    value={fmtInt(m.n_train)} />
        <MetricCard t={t} label="Test rows"     value={fmtInt(m.n_test)} />
        <MetricCard t={t} label="Suburb bins"   value={fmtInt(m.top_n_suburbs)} />
      </div>

      {/* Feature importance */}
      <div style={{ padding: "14px 16px 8px", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                       textTransform: "uppercase", color: t.textMuted, marginBottom: 8 }}>
          Top feature importance
        </div>
        <ResponsiveContainer width="100%" height={Math.max(220, fi.length * 22)}>
          <BarChart data={fi} layout="vertical" margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
            <CartesianGrid stroke={t.gridDot} strokeDasharray="2 4" />
            <XAxis type="number" stroke={t.textMuted} fontSize={11} domain={[0, "dataMax"]} tickFormatter={(v) => (v * 100).toFixed(0) + "%"} />
            <YAxis type="category" dataKey="name" stroke={t.textMuted} fontSize={11} width={150} />
            <Tooltip
              cursor={{ fill: t.rowHover }}
              contentStyle={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 12 }}
              formatter={(v) => (v * 100).toFixed(1) + "%"}
            />
            <Bar dataKey="importance" fill={t.accent} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Residuals scatter */}
      <div style={{ padding: "14px 16px 8px", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                      textTransform: "uppercase", color: t.textMuted, marginBottom: 8 }}>
          Actual vs predicted ({res.length} sample)
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 4, right: 12, left: 0, bottom: 4 }}>
            <CartesianGrid stroke={t.gridDot} strokeDasharray="2 4" />
            <XAxis type="number" dataKey="actual"    stroke={t.textMuted} fontSize={11}
                   tickFormatter={(v) => fmtAud(v, { short: true })} name="Actual" />
            <YAxis type="number" dataKey="predicted" stroke={t.textMuted} fontSize={11}
                   tickFormatter={(v) => fmtAud(v, { short: true })} name="Predicted" />
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: 5_000_000, y: 5_000_000 }]}
              stroke={t.accent2} strokeDasharray="4 4"
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 12 }}
              formatter={(v) => fmtAud(v)}
            />
            <Scatter data={res} fill={t.accent} opacity={0.55} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


// Skeleton placeholders for the Model Explorer's metric grid + two charts.
// Matches the real layout's spacing and card frames so when the data lands
// the only thing that changes is the content of the rectangles.
function ModelExplorerSkeleton({ t }) {
  const card = {
    background: t.surface,
    border: `1px solid ${t.border}`,
    borderRadius: 10,
  };
  const bar = (w, h = 10, op = 0.6) => ({
    height: h, width: w,
    background: t.borderBright,
    borderRadius: 4,
    opacity: op,
  });
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ ...card, padding: "12px 14px", opacity: 0.65 - i * 0.03 }}>
            <div style={bar("55%", 8, 0.55)} />
            <div style={{ ...bar("40%", 16, 0.7), marginTop: 8 }} />
          </div>
        ))}
      </div>

      <div style={{ ...card, padding: "14px 16px", height: 280, opacity: 0.6 }}>
        <div style={bar("28%", 8)} />
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 14 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={bar(`${88 - i * 8}%`, 10, 0.55 - i * 0.05)} />
          ))}
        </div>
      </div>

      <div style={{ ...card, padding: "14px 16px", height: 280, opacity: 0.5 }}>
        <div style={bar("32%", 8)} />
        <div style={{ position: "relative", marginTop: 14, height: 220, overflow: "hidden" }}>
          {Array.from({ length: 32 }).map((_, i) => {
            const seed = (i * 9301 + 49297) % 233280 / 233280;
            const x = 6 + seed * 88;
            const y = 6 + ((i * 7) % 92);
            return (
              <span key={i} style={{
                position: "absolute",
                left: `${x}%`, top: `${y}%`,
                width: 7, height: 7, borderRadius: "50%",
                background: t.accent,
                opacity: 0.18,
              }} />
            );
          })}
          <span style={{
            position: "absolute",
            left: 0, bottom: 0,
            width: "100%", height: 1,
            background: t.borderBright,
            transformOrigin: "left bottom",
            transform: "rotate(-22deg)",
            opacity: 0.45,
          }} />
        </div>
      </div>
    </div>
  );
}


/* ============================== Shared bits ============================== */

function MetricCard({ t, label, value }) {
  return (
    <div style={{
      padding: "12px 14px",
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 10,
    }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
                    textTransform: "uppercase", color: t.textMuted, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 600, color: t.text }}>{value}</div>
    </div>
  );
}

function Field({ t, label, children }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.04em",
                      textTransform: "uppercase", color: t.textMuted }}>{label}</span>
      {children}
    </label>
  );
}

function NumField({ t, label, value, onChange, ...rest }) {
  return (
    <Field t={t} label={label}>
      <input type="number" value={value} onChange={onChange} style={inputStyle(t)} {...rest} />
    </Field>
  );
}

function inputStyle(t) {
  return {
    padding: "8px 10px",
    background: t.bg,
    border: `1px solid ${t.border}`,
    borderRadius: 8,
    color: t.text,
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
  };
}

function prettifyFeature(s) {
  if (!s) return "—";
  return s
    .replace(/_/g, " ")
    .replace(/\bsuburb (lat|lng)\b/g, (_, x) => `Suburb ${x === "lat" ? "latitude" : "longitude"}`)
    .replace(/\bsuburb sqkm\b/g, "Suburb size (sqkm)")
    .replace(/\bnum (bed|bath|parking)\b/g, (_, x) => `Num ${x}`)
    .replace(/\b\w/g, (m) => m.toUpperCase());
}
