// Vite proxy forwards /orb, /dashboard, etc. to http://localhost:8000 in dev,
// so an empty base means "same origin". Override via VITE_API_BASE_URL for
// the deployed (Phase 2) build.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

// Demo write token. The operator opens the site once with
// ?write_token=<value>; we stash it in sessionStorage, scrub it from the
// URL, and send it as X-Write-Token on every API + orb call. It unlocks
// lead status writes, exempts the session from rate limits, and marks
// orb runs as trusted (prompt shown verbatim on the Dashboard feed).
const TOKEN_KEY = "rai_write_token";

function captureTokenFromUrl() {
  try {
    const url = new URL(window.location.href);
    const token = url.searchParams.get("write_token");
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token);
      url.searchParams.delete("write_token");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    }
  } catch { /* SSR / storage blocked */ }
}
captureTokenFromUrl();

export function writeToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; }
}

export function authHeaders() {
  const token = writeToken();
  return token ? { "X-Write-Token": token } : {};
}
