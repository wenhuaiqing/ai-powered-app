// Double Catchment — where the Wishart State School (primary) and Mansfield
// State High School catchments overlap in Brisbane, QLD 4122.
//
// Entirely client-side: no backend, database or AI. The polygons are bundled
// JSON from the QLD Government SchoolsAndSchoolCatchments spatial service
// (data currency 22/07/2026) and the point-in-polygon check runs in the
// browser. The basemap is the same OpenStreetMap tile layer Market Insights
// uses, so the CSP already permits it.

import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import {
  CircleMarker, GeoJSON, MapContainer, Marker, Pane, ScaleControl,
  TileLayer, Tooltip, useMapEvents,
} from "react-leaflet";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useIsMobile } from "../../lib/useMediaQuery.js";

// ---------------------------------------------------------------------------
// Static content
// ---------------------------------------------------------------------------

const SUBURB_CENTRES = {
  Wishart: [-27.5560, 153.0970],
  Mansfield: [-27.5385, 153.1045],
  "Upper Mount Gravatt": [-27.5545, 153.0810],
  "Mount Gravatt East": [-27.5390, 153.0870],
  Mackenzie: [-27.5460, 153.1185],
  Rochedale: [-27.5720, 153.1195],
  "Eight Mile Plains": [-27.5740, 153.0960],
  Carindale: [-27.5230, 153.1090],
};

const EDGES = [
  {
    side: "North", zone: "wss", caption: "Wishart SS line",
    text: <>
      <b>Newnham Road</b> east from Dykes Street, then <b>Broadwater Road</b> past Alberon and
      Mailey Streets to about Catania Street. North of this line the primary zone is Mount Gravatt
      East SS or Mansfield SS, but you are still in Mansfield SHS.
    </>,
  },
  {
    side: "East", zone: "wss", caption: "Wishart SS line",
    text: <>
      South from Broadwater Road through <b>Catania Street</b> and <b>Hibiscus Close</b>, across{" "}
      <b>Mount Gravatt-Capalaba Road</b> near the Wishart Village shops, then <b>St Clair Crescent</b>,{" "}
      <b>Hurlstone Street</b> and Andree Place down to the creek. East of this line, roughly a third
      of Wishart, feeds Mansfield SS for primary and is still in Mansfield SHS.
    </>,
  },
  {
    side: "South", zone: "both", caption: "Both lines",
    text: <>
      <b>Bulimba Creek</b>, the suburb boundary with Eight Mile Plains, west to about Kavanagh Road.
      Both zones stop at the creek here.
    </>,
  },
  {
    side: "South-west", zone: "mshs", caption: "Mansfield SHS line",
    text: <>
      The high school zone cuts back into Wishart along <b>Delavan Street</b>, <b>Sieben Street</b>,{" "}
      <b>Barcelona Street</b>, <b>Amsterdam Street</b> and <b>Copenhagen Street</b> up to Mount
      Gravatt-Capalaba Road. The pocket south-west of that line, around Fulton, Remsen and Martense
      Streets, is in Wishart but zoned to MacGregor SHS, so it is not double catchment.
    </>,
  },
  {
    side: "West", zone: "mshs", caption: "Mansfield SHS line",
    text: <>
      Through Upper Mount Gravatt along <b>Dawson Road</b>, Lumley, Hertford and Dupre Streets,{" "}
      <b>Wanda Road</b>, Somerfield Street and Katarina Court back to Dykes Street. West of this line
      is still Wishart SS for primary but Mount Gravatt SHS for high school.
    </>,
  },
];

const AREAS = [
  { label: "Mansfield SHS catchment", km2: "33.15" },
  { label: "Wishart SS catchment", km2: "3.95" },
  { label: "Double catchment", km2: "3.14", strong: true },
  { label: "Wishart suburb", km2: "4.29" },
];

const WHERE = [
  { label: "Wishart", pct: 67.7, text: "2.13 km² · 68%" },
  { label: "Upper Mount Gravatt", pct: 24.4, text: "0.76 km² · 24%" },
  { label: "Mansfield", pct: 5.3, text: "0.17 km² · 5%" },
  { label: "Mount Gravatt East", pct: 2.6, text: "0.08 km² · 3%" },
];

const PRIMARY_SHARE = [
  { label: "Wishart SS", pct: "53%" },
  { label: "Mansfield SS (east, Ham Road side)", pct: "32%", muted: true },
  { label: "Mackenzie State Primary (far east, near the Gateway)", pct: "8%", muted: true },
  { label: "Upper Mount Gravatt SS (south-west pocket)", pct: "7%", muted: true },
];

const HIGH_SHARE = [
  { label: "Mansfield SHS", pct: "89%" },
  { label: "MacGregor SHS (south-west pocket)", pct: "11%", muted: true },
];

const CAVEATS = [
  <><b>Confirm the address on EdMap.</b> These polygons are the Department of Education's published
    2026 boundaries, but EdMap is what the school will use, and street-level edges can shift by a lot.</>,
  <><b>Mansfield SHS enforces the line.</b> It is enrolment-managed, so you need proof of principal
    residence such as a lease or contract plus utility bills. Being one street outside means no place.</>,
  <><b>Boundaries are reviewed yearly.</b> Wishart SS's plan was gazetted 29/08/2025. Buying for a
    child who starts in several years carries some boundary risk.</>,
  <><b>Junior and senior Mansfield zones are identical</b> in the 2026 data, so there is no Year 10
    surprise.</>,
];

const CATCHMENT_SERVICE =
  "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Society/SchoolsAndSchoolCatchments/MapServer";
const EDMAP = "https://www.qgso.qld.gov.au/maps/edmap/";

// ---------------------------------------------------------------------------
// Geometry helpers (GeoJSON Polygon, coordinates as [lng, lat])
// ---------------------------------------------------------------------------

const feat = (geometry) => ({ type: "Feature", properties: {}, geometry });

function inRing(ring, x, y) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function inPolygon(poly, lng, lat) {
  const [outer, ...holes] = poly.coordinates;
  if (!inRing(outer, lng, lat)) return false;
  return !holes.some((h) => inRing(h, lng, lat));
}

function boundsOf(poly) {
  let s = 90, n = -90, w = 180, e = -180;
  for (const [x, y] of poly.coordinates[0]) {
    if (y < s) s = y;
    if (y > n) n = y;
    if (x < w) w = x;
    if (x > e) e = x;
  }
  return L.latLngBounds([s, w], [n, e]);
}

const shortName = (n) => n.replace("State Primary School", "SPS");

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DoubleCatchment() {
  const { t, isDark } = useTheme();
  const isMobile = useIsMobile();
  const [data, setData] = useState(null);
  const [layers, setLayers] = useState({ both: true, wss: true, mshs: true, prim: false, sub: true });
  const [hit, setHit] = useState(null);

  // Lazy-load the 200 KB polygon bundle so it stays out of the main chunk.
  useEffect(() => {
    let cancelled = false;
    import("../../data/wishart-catchment.json").then((m) => { if (!cancelled) setData(m.default); });
    return () => { cancelled = true; };
  }, []);

  // Zone colours mapped onto the Reapit palette: orange for the primary zone,
  // indigo for the high school zone, teal where both apply.
  const zone = useMemo(() => ({
    wss: t.dot.yellow,
    mshs: t.accent,
    both: t.accent2,
    other: t.textDim,
    suburb: t.textMuted,
  }), [t]);

  const subs = useMemo(() => (data ? { Wishart: data.wishart, ...data.suburbs } : null), [data]);

  const pick = ({ lat, lng }) => {
    if (!data) return;
    const w = inPolygon(data.wss, lng, lat);
    const m = inPolygon(data.mshs, lng, lat);
    let prim = w ? "Wishart SS" : null;
    if (!prim) {
      for (const [n, g] of Object.entries(data.primaries)) {
        if (inPolygon(g, lng, lat)) { prim = shortName(n); break; }
      }
    }
    let sub = null;
    for (const [n, g] of Object.entries(subs)) {
      if (inPolygon(g, lng, lat)) { sub = n; break; }
    }
    const shs = m
      ? "Mansfield SHS"
      : sub === "Wishart" || sub === "Upper Mount Gravatt"
        ? "Not Mansfield (MacGregor or Mount Gravatt SHS)"
        : "Not Mansfield SHS";
    setHit({ lat, lng, prim, sub, shs, kind: w && m ? "both" : w ? "wss" : m ? "mshs" : "none" });
  };

  const toggle = (k) => setLayers((s) => ({ ...s, [k]: !s[k] }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <MapStyles t={t} zone={zone} isDark={isDark} />

      <header style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-end", gap: "10px 24px" }}>
        <div>
          <Eyebrow t={t} style={{ marginBottom: 6 }}>Brisbane · QLD 4122 · 2026 catchment boundaries</Eyebrow>
          <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
            Double Catchment
          </h1>
          <p style={{ margin: 0, fontSize: 13, color: t.textMuted, maxWidth: "68ch", lineHeight: 1.55 }}>
            The 3.14 km² where a home sits inside both the Wishart State School zone and the Mansfield
            State High School zone. About two thirds of it is in Wishart itself. The rest spills west
            into Upper Mount Gravatt and north across Broadwater Road into Mansfield and Mount Gravatt East.
          </p>
        </div>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, color: t.textMuted }}>
          <Swatch t={t} colour={zone.wss} fill={0.10}>Wishart SS (Prep to 6)</Swatch>
          <Swatch t={t} colour={zone.mshs} fill={0.08}>Mansfield SHS (7 to 12)</Swatch>
          <Swatch t={t} colour={zone.both} fill={0.30}>Both</Swatch>
        </div>
      </header>

      {/* Map card */}
      <section style={{ background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12, overflow: "hidden" }}>
        <div style={{ position: "relative", height: isMobile ? 380 : "min(64vh, 640px)", minHeight: 340 }}>
          {data ? (
            <CatchmentMap
              data={data} subs={subs} layers={layers} zone={zone} t={t}
              hit={hit} onPick={pick} isMobile={isMobile}
            />
          ) : (
            <div style={{ position: "absolute", inset: 0, background: t.surfaceRaised, display: "grid", placeItems: "center", color: t.textMuted, fontSize: 13 }}>
              Loading catchment polygons...
            </div>
          )}
          {!isMobile && (
            <>
              <Panel t={t} style={{ left: 12, bottom: 28 }}>
                <Legend t={t} zone={zone} layers={layers} onToggle={toggle} />
              </Panel>
              <Panel t={t} style={{ right: 12, top: 12, maxWidth: 290 }}>
                <CheckSpot t={t} zone={zone} hit={hit} />
              </Panel>
            </>
          )}
        </div>
        {isMobile && (
          <div style={{ display: "grid", gap: 12, padding: 12, borderTop: `1px solid ${t.border}` }}>
            <CheckSpot t={t} zone={zone} hit={hit} />
            <Legend t={t} zone={zone} layers={layers} onToggle={toggle} />
          </div>
        )}
      </section>

      {/* Narrative + figures */}
      <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "minmax(0, 1.25fr) minmax(0, 1fr)", gap: 12 }}>
        <Card t={t} title="Walking the boundary">
          <Note t={t}>
            Clockwise from the north-west corner at Newnham Road and Dykes Street. Each edge belongs to
            one of the two zones: the north and east edges are where the Wishart SS primary zone ends,
            the south-west and west edges are where the Mansfield SHS zone ends.
          </Note>
          <div style={{ borderTop: `1px solid ${t.rowDivider}`, marginTop: 8 }}>
            {EDGES.map((e) => (
              <div key={e.side} style={{
                display: "grid", gridTemplateColumns: isMobile ? "1fr" : "104px 1fr", gap: isMobile ? 4 : 14,
                padding: "11px 0", borderBottom: `1px solid ${t.rowDivider}`,
              }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: t.text, lineHeight: 1.3 }}>{e.side}</div>
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: zone[e.zone], marginTop: 2 }}>
                    {e.caption}
                  </div>
                </div>
                <Note t={t}>{e.text}</Note>
              </div>
            ))}
          </div>
        </Card>

        <Card t={t} title="What the polygons say">
          <Table t={t} head={["Area", "km²"]} rows={AREAS.map((a) => [
            <span style={{ fontWeight: a.strong ? 700 : 400, color: t.text }}>{a.label}</span>,
            <span style={{ fontWeight: a.strong ? 700 : 500, color: t.text }}>{a.km2}</span>,
          ])} />

          <Eyebrow t={t} style={{ marginTop: 18, marginBottom: 6 }}>Where the double catchment sits</Eyebrow>
          <Table t={t} rows={WHERE.map((w) => [
            <div>
              <span style={{ color: t.text }}>{w.label}</span>
              <div style={{ height: 6, background: t.rowDivider, borderRadius: 3, overflow: "hidden", marginTop: 6 }}>
                <div style={{ width: `${w.pct}%`, height: "100%", background: zone.both }} />
              </div>
            </div>,
            <span style={{ color: t.text, fontWeight: 500 }}>{w.text}</span>,
          ])} />

          <Eyebrow t={t} style={{ marginTop: 18, marginBottom: 6 }}>How Wishart the suburb is zoned</Eyebrow>
          <Table t={t} head={["Primary school", "Share of suburb"]} rows={PRIMARY_SHARE.map((r) => [
            <span style={{ color: r.muted ? t.textMuted : t.text }}>{r.label}</span>,
            <span style={{ color: t.text, fontWeight: 500 }}>{r.pct}</span>,
          ])} />
          <Table t={t} head={["High school", ""]} rows={HIGH_SHARE.map((r) => [
            <span style={{ color: r.muted ? t.textMuted : t.text }}>{r.label}</span>,
            <span style={{ color: t.text, fontWeight: 500 }}>{r.pct}</span>,
          ])} style={{ marginTop: 10 }} />
          <Note t={t} style={{ marginTop: 12 }}>
            So <b>just under half of Wishart by area</b> is true double catchment. Nearly all of the
            suburb gets Mansfield SHS. The primary zone is what varies.
          </Note>
        </Card>

        <Card t={t} title="Before you rely on it">
          <Bullets t={t} items={CAVEATS} />
        </Card>

        <Card t={t} title="Sources">
          <Bullets t={t} items={[
            <>Catchment and school polygons: Queensland Government{" "}
              <a href={CATCHMENT_SERVICE} target="_blank" rel="noreferrer" style={{ color: t.accent, textDecoration: "underline" }}>SchoolsAndSchoolCatchments</a>{" "}
              spatial service, data currency {data?.currency || "22/07/2026"}.</>,
            <>Suburb boundaries: Queensland Government AdministrativeBoundaries locality layer.</>,
            <>Basemap: OpenStreetMap contributors. Street names on boundary edges from Nominatim reverse
              geocoding at about 250 m intervals.</>,
            <>Official address lookup:{" "}
              <a href={EDMAP} target="_blank" rel="noreferrer" style={{ color: t.accent, textDecoration: "underline" }}>EdMap</a>.</>,
          ]} />
        </Card>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 24px", fontSize: 12, color: t.textDim, padding: "4px 2px 8px" }}>
        <span>Areas computed on GDA2020 with Turf.js. Rounded to two decimals.</span>
        <span>Boundaries current as at 09/09/2026.</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Map
// ---------------------------------------------------------------------------

function CatchmentMap({ data, subs, layers, zone, t, hit, onPick, isMobile }) {
  const bounds = useMemo(() => boundsOf(data.wss), [data]);
  // On desktop the legend and check panels overlay the map, so fit the
  // Wishart SS zone into the space they leave free.
  const fit = isMobile
    ? { padding: [24, 24] }
    : { paddingTopLeft: [40, 24], paddingBottomRight: [310, 40] };
  const blank = useMemo(() => L.divIcon({ className: "", iconSize: [0, 0] }), []);
  const styles = useMemo(() => ({
    mshs: { color: zone.mshs, weight: 2.2, fillColor: zone.mshs, fillOpacity: 0.06 },
    wss: { color: zone.wss, weight: 2.2, fillColor: zone.wss, fillOpacity: 0.08 },
    both: { color: zone.both, weight: 2.6, fillColor: zone.both, fillOpacity: 0.28 },
    prim: { color: zone.other, weight: 1.2, dashArray: "4 4", fill: false },
    sub: { color: zone.suburb, weight: 1, dashArray: "1 4", fill: false, opacity: 0.9 },
  }), [zone]);

  const isKey = (n) => n === "Wishart SS" || n === "Mansfield SHS";
  const schoolColour = (n) => (n === "Wishart SS" ? zone.wss : n === "Mansfield SHS" ? zone.mshs : t.textMuted);
  const schoolClass = (n) => (n === "Wishart SS" ? "dc-lbl-wss" : n === "Mansfield SHS" ? "dc-lbl-mshs" : "");

  return (
    <MapContainer
      className="dc-map"
      bounds={bounds}
      boundsOptions={fit}
      maxBounds={bounds.pad(1.6)}
      minZoom={12}
      maxZoom={17}
      zoomSnap={0.5}
      scrollWheelZoom
      style={{ height: "100%", width: "100%", background: t.bg, fontFamily: "inherit" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ScaleControl position="bottomright" imperial={false} />
      <ClickProbe onPick={onPick} />

      {/* Panes fix the stacking order regardless of toggle order. */}
      <Pane name="dc-sub" style={{ zIndex: 405 }}>
        {layers.sub && Object.entries(subs).map(([n, g]) => (
          <GeoJSON key={n} data={feat(g)} style={styles.sub} interactive={false} />
        ))}
      </Pane>
      <Pane name="dc-prim" style={{ zIndex: 406 }}>
        {layers.prim && Object.entries(data.primaries).map(([n, g]) => (
          <GeoJSON key={n} data={feat(g)} style={styles.prim} interactive={false} />
        ))}
      </Pane>
      <Pane name="dc-mshs" style={{ zIndex: 410 }}>
        {layers.mshs && <GeoJSON data={feat(data.mshs)} style={styles.mshs} interactive={false} />}
      </Pane>
      <Pane name="dc-wss" style={{ zIndex: 411 }}>
        {layers.wss && <GeoJSON data={feat(data.wss)} style={styles.wss} interactive={false} />}
      </Pane>
      <Pane name="dc-both" style={{ zIndex: 412 }}>
        {layers.both && <GeoJSON data={feat(data.both)} style={styles.both} interactive={false} />}
      </Pane>

      {/* Suburb labels ride with the suburb boundary toggle. */}
      {layers.sub && Object.entries(SUBURB_CENTRES).map(([n, pos]) => (
        <Marker key={n} position={pos} icon={blank} interactive={false} keyboard={false}>
          <Tooltip permanent direction="center" className="dc-lbl dc-lbl-suburb" opacity={1}>
            {n.toUpperCase()}
          </Tooltip>
        </Marker>
      ))}

      {/* School sites and the clicked pin */}
      <Pane name="dc-schools" style={{ zIndex: 620 }}>
        {Object.entries(data.sites).map(([n, [lng, lat]]) => (
          <CircleMarker
            key={n}
            center={[lat, lng]}
            radius={isKey(n) ? 6 : 4.5}
            interactive={false}
            pathOptions={{ color: t.surface, weight: 2, fillColor: schoolColour(n), fillOpacity: 1 }}
          />
        ))}
        {hit && (
          <CircleMarker
            center={[hit.lat, hit.lng]}
            radius={7}
            interactive={false}
            pathOptions={{ color: t.surface, weight: 2.5, fillColor: zone[hit.kind === "none" ? "suburb" : hit.kind], fillOpacity: 1 }}
          />
        )}
      </Pane>
      {Object.entries(data.sites).map(([n, [lng, lat]]) => {
        const left = n === "Upper Mount Gravatt SS";
        return (
          <Marker key={n} position={[lat, lng]} icon={blank} interactive={false} keyboard={false}>
            <Tooltip
              permanent
              direction={left ? "left" : "right"}
              offset={[left ? -8 : 8, 0]}
              className={`dc-lbl dc-lbl-school ${schoolClass(n)}`}
              opacity={1}
            >
              {shortName(n)}
            </Tooltip>
          </Marker>
        );
      })}
    </MapContainer>
  );
}

function ClickProbe({ onPick }) {
  useMapEvents({ click: (e) => onPick(e.latlng) });
  return null;
}

// Leaflet renders tooltips and controls outside React's inline styles, so the
// overrides live in a scoped style block keyed to the theme.
function MapStyles({ t, zone, isDark }) {
  const tileFilter = isDark
    ? "filter: invert(1) hue-rotate(180deg) brightness(.82) contrast(.9) saturate(.5);"
    : "";
  return (
    <style>{`
      .dc-map .leaflet-tile-pane { ${tileFilter} }
      .dc-map .leaflet-bar { border: 1px solid ${t.border}; box-shadow: none; border-radius: 8px; overflow: hidden; }
      .dc-map .leaflet-bar a { background: ${t.surface}; color: ${t.text}; border-bottom-color: ${t.border}; }
      .dc-map .leaflet-bar a:hover { background: ${t.rowHover}; }
      .dc-map .leaflet-bar a.leaflet-disabled { color: ${t.textDim}; }
      .dc-map .leaflet-control-attribution { background: ${t.surface}; color: ${t.textMuted}; font-size: 10px; font-family: inherit; border-radius: 6px 0 0 0; }
      .dc-map .leaflet-control-attribution a { color: ${t.textMuted}; }
      .dc-map .leaflet-control-scale-line { background: ${t.surface}; border-color: ${t.textMuted}; color: ${t.textMuted}; font-size: 10px; font-family: inherit; }
      .dc-map .leaflet-tooltip.dc-lbl { background: none; border: 0; box-shadow: none; padding: 0; white-space: nowrap; font-family: inherit; text-shadow: 0 0 3px ${t.surface}, 0 0 3px ${t.surface}, 0 0 6px ${t.surface}; }
      .dc-map .leaflet-tooltip.dc-lbl::before { display: none; }
      .dc-map .dc-lbl-suburb { font-size: 12px; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: ${t.textMuted}; }
      .dc-map .dc-lbl-school { font-size: 11px; font-weight: 600; color: ${t.text}; }
      .dc-map .dc-lbl-wss { color: ${zone.wss}; }
      .dc-map .dc-lbl-mshs { color: ${zone.mshs}; }
      .dc-note b { color: ${t.text}; font-weight: 600; }
    `}</style>
  );
}

// ---------------------------------------------------------------------------
// Panels
// ---------------------------------------------------------------------------

function Panel({ t, style, children }) {
  return (
    <div style={{
      position: "absolute", zIndex: 1000,
      background: t.surface, border: `1px solid ${t.border}`, borderRadius: 10,
      padding: "10px 12px", fontSize: 12.5, lineHeight: 1.35, boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
      ...style,
    }}>{children}</div>
  );
}

const LEGEND_ROWS = [
  { key: "both", label: "Double catchment" },
  { key: "wss", label: "Wishart SS catchment" },
  { key: "mshs", label: "Mansfield SHS catchment" },
  { key: "prim", label: "Neighbouring primary zones" },
  { key: "sub", label: "Suburb boundaries" },
];

function Legend({ t, zone, layers, onToggle }) {
  return (
    <div style={{ display: "grid", gap: 7, minWidth: 210 }}>
      <Eyebrow t={t}>Layers</Eyebrow>
      {LEGEND_ROWS.map((r) => (
        <label key={r.key} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", userSelect: "none", color: t.text, fontSize: 12.5 }}>
          <input type="checkbox" checked={layers[r.key]} onChange={() => onToggle(r.key)} style={{ margin: 0, accentColor: t.accent }} />
          <LegendSwatch zone={zone} kind={r.key} />
          {r.label}
        </label>
      ))}
    </div>
  );
}

function LegendSwatch({ zone, kind }) {
  const base = { width: 20, height: 11, borderRadius: 2, display: "inline-block", flexShrink: 0, boxSizing: "border-box" };
  if (kind === "prim") return <i style={{ ...base, border: `1.5px dashed ${zone.other}` }} />;
  if (kind === "sub") return <i style={{ ...base, height: 0, borderRadius: 0, borderTop: `1.5px dotted ${zone.suburb}` }} />;
  const fill = { both: 0.30, wss: 0.10, mshs: 0.08 }[kind];
  return <i style={{ ...base, border: `2px solid ${zone[kind]}`, background: withAlpha(zone[kind], fill) }} />;
}

function Swatch({ t, colour, fill, children }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
      <i style={{ width: 22, height: 12, borderRadius: 2, border: `2px solid ${colour}`, background: withAlpha(colour, fill), display: "inline-block", boxSizing: "border-box" }} />
      <span style={{ color: t.textMuted }}>{children}</span>
    </span>
  );
}

const VERDICT = {
  both: "Double catchment",
  wss: "Wishart SS only",
  mshs: "Mansfield SHS only",
  none: "Neither zone",
};

function CheckSpot({ t, zone, hit }) {
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <Eyebrow t={t}>Check a spot</Eyebrow>
      {!hit ? (
        <div style={{ color: t.textMuted, fontSize: 12.5 }}>
          Click anywhere on the map to see which state schools that address is zoned for.
        </div>
      ) : (
        <>
          <div style={{ fontWeight: 700, fontSize: 15, lineHeight: 1.15, color: hit.kind === "none" ? t.textMuted : zone[hit.kind] }}>
            {VERDICT[hit.kind]}
          </div>
          <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px", margin: 0, fontSize: 12.5 }}>
            <dt style={{ color: t.textMuted }}>Primary</dt>
            <dd style={{ margin: 0, color: t.text }}>{hit.prim || "Outside the mapped primary zones"}</dd>
            <dt style={{ color: t.textMuted }}>High</dt>
            <dd style={{ margin: 0, color: t.text }}>{hit.shs}</dd>
            <dt style={{ color: t.textMuted }}>Suburb</dt>
            <dd style={{ margin: 0, color: t.text }}>{hit.sub || "Outside the mapped suburbs"}</dd>
          </dl>
          <div style={{ fontVariantNumeric: "tabular-nums", color: t.textDim, fontSize: 11.5 }}>
            {hit.lat.toFixed(5)}, {hit.lng.toFixed(5)}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

function Card({ t, title, children }) {
  return (
    <section style={{ padding: "14px 16px 12px", background: t.surface, border: `1px solid ${t.border}`, borderRadius: 12, minWidth: 0 }}>
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: t.textMuted, marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </section>
  );
}

function Eyebrow({ t, style, children }) {
  return (
    <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: t.textMuted, ...style }}>
      {children}
    </div>
  );
}

function Note({ t, style, children }) {
  return (
    <p className="dc-note" style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: t.textMuted, maxWidth: "64ch", ...style }}>
      {children}
    </p>
  );
}

function Bullets({ t, items }) {
  return (
    <ul className="dc-note" style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 13, lineHeight: 1.55, color: t.textMuted, maxWidth: "64ch" }}>
      {items.map((it, i) => <li key={i}>{it}</li>)}
    </ul>
  );
}

function Table({ t, head, rows, style }) {
  const th = { textAlign: "left", padding: "6px 0", fontSize: 10.5, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: t.textMuted, borderBottom: `1px solid ${t.rowDivider}` };
  const td = { padding: "8px 0", borderBottom: `1px solid ${t.rowDivider}`, verticalAlign: "top", fontSize: 13 };
  return (
    <table style={{ borderCollapse: "collapse", width: "100%", fontVariantNumeric: "tabular-nums", ...style }}>
      {head && (
        <thead>
          <tr>
            <th style={th}>{head[0]}</th>
            <th style={{ ...th, textAlign: "right", whiteSpace: "nowrap" }}>{head[1]}</th>
          </tr>
        </thead>
      )}
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td style={td}>{r[0]}</td>
            <td style={{ ...td, textAlign: "right", whiteSpace: "nowrap", paddingLeft: 12 }}>{r[1]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Theme colours are hex; return an rgba() with the given alpha for fills.
function withAlpha(hex, alpha) {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}
