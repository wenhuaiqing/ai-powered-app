// Market Insights — Recharts dashboards (price distribution, price vs distance,
// beds breakdown, top suburbs) and a Leaflet bubble map of suburb medians.

import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api, fmtAud, fmtInt } from "../../lib/api.js";
import { useIsMobile } from "../../lib/useMediaQuery.js";

export default function MarketInsights() {
  const { t } = useTheme();
  const isMobile = useIsMobile();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api("/api/insights/price-distribution"),
      api("/api/insights/price-vs-distance"),
      api("/api/insights/beds-breakdown"),
      api("/api/insights/top-suburbs?limit=12"),
      api("/api/insights/suburb-medians?limit=300"),
    ])
      .then(([dist, pvd, beds, top, map]) => {
        if (!cancelled) setData({ dist, pvd, beds, top, map });
      })
      .catch((e) => { if (!cancelled) setError(String(e?.message || e)); })
      .finally(()=> { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <header>
        <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
          Market Insights
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: t.textMuted }}>
          Aggregates over 11,160 NSW property sales. The same DuckDB the Data Query agent runs against.
        </p>
      </header>

      {loading && <SkeletonGrid t={t} />}
      {error && (
        <div style={{ padding: "10px 12px", background: t.dotGlow.red, color: t.dot.red, border: `1px solid ${t.dot.red}`, borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {data && (
        <>
          <div style={{
            display: "grid",
            // Drop the 340px min on mobile so charts go single-column without
            // forcing horizontal overflow on phones.
            gridTemplateColumns: isMobile ? "1fr" : "repeat(auto-fit, minmax(340px, 1fr))",
            gap: 12,
          }}>
            <Card t={t} title="Price distribution (≤$5M)">
              <PriceDistribution t={t} bins={data.dist.bins} />
            </Card>
            <Card t={t} title="Average price by km from CBD">
              <PriceVsDistance t={t} points={data.pvd.points} />
            </Card>
            <Card t={t} title="Bedrooms breakdown">
              <BedsBreakdown t={t} breakdown={data.beds.breakdown} />
            </Card>
            <Card t={t} title="Top suburbs by median price">
              <TopSuburbs t={t} suburbs={data.top.suburbs} />
            </Card>
          </div>

          <Card t={t} title="Suburb median price (bubble map)">
            <SuburbMap t={t} suburbs={data.map.suburbs} isMobile={isMobile} />
          </Card>
        </>
      )}
    </div>
  );
}

function SkeletonGrid({ t }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 12 }}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} style={{ height: 240, background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12, opacity: 0.6 - i * 0.05 }} />
      ))}
    </div>
  );
}

function Card({ t, title, children }) {
  return (
    <section style={{
      padding: "14px 16px 8px",
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 12,
      minHeight: 280,
      display: "flex",
      flexDirection: "column",
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em",
                    textTransform: "uppercase", color: t.textMuted, marginBottom: 8 }}>
        {title}
      </div>
      <div style={{ flex: 1, minHeight: 220 }}>
        {children}
      </div>
    </section>
  );
}


function PriceDistribution({ t, bins }) {
  const data = bins.map((b) => ({ ...b, label: `$${(b.price_bucket / 1_000).toFixed(0)}k` }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 6, left: 4, bottom: 4 }}>
        <CartesianGrid stroke={t.gridDot} strokeDasharray="2 4" />
        <XAxis dataKey="price_bucket" stroke={t.textMuted} fontSize={10}
               tickFormatter={(v) => fmtAud(v, { short: true })} interval="preserveStartEnd" />
        <YAxis stroke={t.textMuted} fontSize={11} />
        <Tooltip
          cursor={{ fill: t.rowHover }}
          contentStyle={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 12 }}
          labelFormatter={(v) => `${fmtAud(v)} bucket`}
          formatter={(v) => [fmtInt(v), "sales"]}
        />
        <Bar dataKey="n" fill={t.accent} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function PriceVsDistance({ t, points }) {
  const data = points.map((p) => ({ x: p.km_from_cbd, y: p.avg_price, n: p.n }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ScatterChart margin={{ top: 4, right: 6, left: 4, bottom: 4 }}>
        <CartesianGrid stroke={t.gridDot} strokeDasharray="2 4" />
        <XAxis type="number" dataKey="x" stroke={t.textMuted} fontSize={11} name="km from CBD" unit=" km" />
        <YAxis type="number" dataKey="y" stroke={t.textMuted} fontSize={11}
               tickFormatter={(v) => fmtAud(v, { short: true })} name="Avg price" />
        <ZAxis type="number" dataKey="n" range={[20, 200]} />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 12 }}
          formatter={(v, name) => name === "Avg price" ? fmtAud(v) : v}
        />
        <Scatter data={data} fill={t.accent} opacity={0.55} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function BedsBreakdown({ t, breakdown }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={breakdown} margin={{ top: 4, right: 6, left: 4, bottom: 4 }}>
        <CartesianGrid stroke={t.gridDot} strokeDasharray="2 4" />
        <XAxis dataKey="num_bed" stroke={t.textMuted} fontSize={11} tickFormatter={(v) => `${v} bd`} />
        <YAxis stroke={t.textMuted} fontSize={11}
               tickFormatter={(v) => fmtAud(v, { short: true })} />
        <Tooltip
          cursor={{ fill: t.rowHover }}
          contentStyle={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 12 }}
          formatter={(v) => fmtAud(v)}
          labelFormatter={(v) => `${v} bedroom${v === 1 ? "" : "s"}`}
        />
        <Bar dataKey="median_price" name="Median price" fill={t.accent}  radius={[4, 4, 0, 0]} />
        <Bar dataKey="avg_price"    name="Average price" fill={t.accent2} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function TopSuburbs({ t, suburbs }) {
  return (
    <div style={{ height: 220, overflowY: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ position: "sticky", top: 0, background: t.surface, textAlign: "left", color: t.textMuted }}>
            <th style={{ padding: "6px 8px", fontWeight: 600 }}>Suburb</th>
            <th style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Median</th>
            <th style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>Sales</th>
            <th style={{ padding: "6px 8px", fontWeight: 600, textAlign: "right" }}>km/CBD</th>
          </tr>
        </thead>
        <tbody>
          {suburbs.map((s) => (
            <tr key={s.suburb} style={{ borderTop: `1px solid ${t.rowDivider}` }}>
              <td style={{ padding: "6px 8px", color: t.text }}>{s.suburb}</td>
              <td style={{ padding: "6px 8px", textAlign: "right", fontWeight: 600 }}>
                {fmtAud(s.median_price, { short: true })}
              </td>
              <td style={{ padding: "6px 8px", textAlign: "right", color: t.textMuted }}>{s.sales}</td>
              <td style={{ padding: "6px 8px", textAlign: "right", color: t.textMuted }}>{s.avg_km_from_cbd}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SuburbMap({ t, suburbs, isMobile }) {
  const prices = suburbs.map((s) => s.median_price).filter((p) => p > 0);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const radius = (p) => {
    if (!isFinite(min) || max === min) return 8;
    return 4 + ((p - min) / (max - min)) * 20;
  };
  return (
    <div style={{ height: isMobile ? 280 : 360, overflow: "hidden", borderRadius: 8, border: `1px solid ${t.border}` }}>
      <MapContainer center={[-33.86, 151.13]} zoom={10} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {suburbs.map((s, i) => (
          <CircleMarker
            key={i}
            center={[s.lat, s.lng]}
            radius={radius(s.median_price)}
            pathOptions={{ color: t.accent, fillColor: t.accent, fillOpacity: 0.35, weight: 1 }}
          >
            <Popup>
              <div style={{ fontSize: 12, fontFamily: "Inter, sans-serif" }}>
                <strong>{s.suburb}</strong><br />
                Median: {fmtAud(s.median_price)}<br />
                {s.n} sales
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
