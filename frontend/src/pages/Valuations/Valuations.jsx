// Valuations module — two tabs:
//   Predictor: form -> /api/valuations/predict -> predicted price + contributions bar
//   Model Explorer: /api/valuations/model-info -> metrics + feature importance + residuals

import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, Cell,
} from "recharts";
import { Calculator, LineChart as LineIcon, Sparkles } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtInt } from "../../lib/api.js";

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
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <header>
        <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
          Valuations
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: t.textMuted }}>
          RandomForest trained on 11,049 NSW sales (MAE ≈ $270k, R² ≈ 0.745).
        </p>
      </header>

      <Tabs t={t} value={tab} onChange={setTab} />

      {tab === "predictor" ? <Predictor t={t} /> : <ModelExplorer t={t} />}
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

function Predictor({ t }) {
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
    <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, 360px) 1fr", gap: 18 }}>
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
          <input
            type="text"
            value={form.suburb}
            onChange={update("suburb")}
            style={inputStyle(t)}
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
        {result && <ResultBlock t={t} result={result} />}
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

function ResultBlock({ t, result }) {
  const ci = result.confidence_interval || [0, 0];
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

function ModelExplorer({ t }) {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api("/api/valuations/model-info")
      .then((d)  => { if (!cancelled) setInfo(d); })
      .catch((e) => { if (!cancelled) setError(String(e?.message || e)); })
      .finally(()=> { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div style={{ color: t.textMuted, fontSize: 13 }}>Loading model info…</div>;
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
