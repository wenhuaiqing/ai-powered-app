// Small fetch helper for /api/* endpoints. Throws on non-2xx with the body
// text as the error message so callers can surface it in the UI.

import { API_BASE_URL } from "../config.js";

export async function api(path, { method = "GET", body, signal } = {}) {
  const opts = {
    method,
    headers: { "Accept": "application/json" },
    signal,
  };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE_URL}${path}`, opts);
  if (!res.ok) {
    let detail = "";
    try { detail = await res.text(); } catch { /* swallow */ }
    throw new Error(`HTTP ${res.status} ${res.statusText}${detail ? ` — ${detail.slice(0, 200)}` : ""}`);
  }
  return res.json();
}

export function fmtAud(value, opts = {}) {
  if (value == null || Number.isNaN(value)) return "—";
  const { decimals = 0, short = false } = opts;
  if (short && Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (short && Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
  return `$${Number(value).toLocaleString("en-AU", { maximumFractionDigits: decimals, minimumFractionDigits: decimals })}`;
}

export function fmtInt(value) {
  if (value == null || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString("en-AU");
}

export function fmtDate(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value).slice(0, 10);
    return d.toLocaleDateString("en-AU", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return String(value).slice(0, 10);
  }
}
