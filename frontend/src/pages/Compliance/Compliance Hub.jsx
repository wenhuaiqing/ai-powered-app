// Compliance Hub — direct RAG search over the NSW regulation corpus.
// Showing the same retrieval that powers the orb's Compliance agent, plus a
// shortcut to fire the full agent (with LLM synthesis + web fallback).

import { useCallback, useState } from "react";
import { ExternalLink, Search, Sparkles } from "lucide-react";
import { useOrb } from "../../context/OrbContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { api } from "../../lib/api.js";

const SAMPLES = [
  "What stamp duty applies to a $900k purchase in NSW?",
  "Maximum bond a landlord can request for a residential tenancy",
  "First Home Buyers Assistance Scheme thresholds",
  "Foreign purchaser surcharge duty in NSW",
  "Strata levies and special levies",
  "Cooling-off period after exchange",
];

export default function ComplianceHub() {
  const { t } = useTheme();
  const orb = useOrb();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = useCallback(async (q) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api(`/api/compliance/search?q=${encodeURIComponent(q)}&k=5`);
      setResults(data);
    } catch (e) {
      setError(String(e?.message || e));
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const onSubmit = (e) => {
    e?.preventDefault();
    search(query);
  };

  const fireAgent = () => {
    if (!query.trim()) return;
    orb.openWithPrompt(query, { module: "compliance" });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 880 }}>
      <header>
        <h1 style={{ margin: "0 0 6px", fontSize: 20, fontWeight: 700, color: t.text, letterSpacing: "-0.01em" }}>
          Compliance Hub
        </h1>
        <p style={{ margin: 0, fontSize: 13, color: t.textMuted }}>
          Cosine retrieval over a curated NSW regulatory corpus (Fair Trading, Residential
          Tenancies Act, stamp duty, FIRB, strata). The orb's Compliance agent uses the same
          retrieval, then adds LLM synthesis and a Tavily web fallback for thin matches.
        </p>
      </header>

      <form onSubmit={onSubmit} style={{
        display: "flex",
        gap: 8,
        padding: "8px 10px",
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 999,
      }}>
        <Search size={16} color={t.textMuted} style={{ alignSelf: "center", marginLeft: 6 }} />
        <input
          autoFocus
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search NSW property regulations..."
          style={{
            flex: 1,
            padding: "8px 4px",
            background: "transparent",
            border: "none",
            color: t.text,
            fontSize: 14,
            fontFamily: "inherit",
            outline: "none",
          }}
        />
        <button type="submit" disabled={loading || !query.trim()} style={{
          padding: "8px 18px",
          background: !query.trim() || loading ? t.accentGlow : t.accent,
          color: !query.trim() || loading ? t.textMuted : "#fff",
          border: "none",
          borderRadius: 999,
          fontSize: 13,
          fontWeight: 600,
          fontFamily: "inherit",
          cursor: !query.trim() || loading ? "not-allowed" : "pointer",
        }}>{loading ? "…" : "Search"}</button>
      </form>

      {/* Sample queries */}
      {!results && !loading && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {SAMPLES.map((s, i) => (
            <button key={i} onClick={() => { setQuery(s); search(s); }} style={{
              fontSize: 12,
              padding: "5px 11px",
              border: `1px dashed ${t.border}`,
              borderRadius: 999,
              background: t.surface,
              color: t.text,
              fontFamily: "inherit",
              cursor: "pointer",
            }}>{s}</button>
          ))}
        </div>
      )}

      {error && (
        <div style={{ padding: "10px 12px", background: t.dotGlow.red, color: t.dot.red, border: `1px solid ${t.dot.red}`, borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {results && (
        <ResultsBlock t={t} results={results} onFireAgent={fireAgent} />
      )}
    </div>
  );
}

function ResultsBlock({ t, results, onFireAgent }) {
  return (
    <>
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "10px 14px",
        background: `linear-gradient(135deg, ${t.accentGlow} 0%, ${t.accent2Glow} 100%)`,
        border: `1px solid ${t.borderBright}`,
        borderRadius: 10,
      }}>
        <Sparkles size={14} color={t.accent2} />
        <span style={{ fontSize: 12, color: t.text, flex: 1 }}>
          Retrieved <b>{results.count}</b> chunk{results.count === 1 ? "" : "s"} for
          <i style={{ marginLeft: 4 }}>{results.query}</i>. Want a synthesised answer with citations?
        </span>
        <button onClick={onFireAgent} style={{
          padding: "6px 14px",
          background: t.accent,
          color: "#fff",
          border: "none",
          borderRadius: 999,
          fontSize: 12,
          fontWeight: 600,
          fontFamily: "inherit",
          cursor: "pointer",
        }}>Ask the agent</button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {results.citations.map((c, i) => (
          <Citation key={i} t={t} c={c} />
        ))}
        {results.citations.length === 0 && (
          <div style={{ padding: 14, fontSize: 13, color: t.textMuted, background: t.surface, border: `1px dashed ${t.border}`, borderRadius: 10 }}>
            No matches in the local corpus. Try the orb's Compliance agent — it will fall back to a Tavily web search.
          </div>
        )}
      </div>
    </>
  );
}

function Citation({ t, c }) {
  return (
    <article style={{
      padding: "14px 16px",
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 10,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: t.text }}>{c.source}</span>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
          padding: "2px 6px", borderRadius: 4,
          background: c.source_type === "web" ? t.dotGlow.yellow : t.accentGlow,
          color: c.source_type === "web" ? t.dot.yellow : t.accent,
        }}>{c.source_type === "web" ? "live web" : "local corpus"}</span>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: t.textMuted }}>score {Number(c.score).toFixed(2)}</span>
      </div>
      <div style={{ fontSize: 13, color: t.text, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>
        {c.snippet}
      </div>
      {c.url && (
        <a href={c.url} target="_blank" rel="noopener noreferrer" style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          marginTop: 8,
          fontSize: 12,
          color: t.accent,
          textDecoration: "underline",
        }}>
          <ExternalLink size={11} />
          {c.url.replace(/^https?:\/\//, "").slice(0, 80)}
        </a>
      )}
    </article>
  );
}
