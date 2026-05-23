// Lets a user override the auto-detected viewport so the demo can be
// previewed in mobile mode from a desktop browser (and back). The override
// is persisted in localStorage so refresh keeps your choice.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const Ctx = createContext(null);
const STORAGE_KEY = "ai-powered-app:viewport-override";
const MOBILE_QUERY = "(max-width: 1024px)";

function readOverride() {
  if (typeof localStorage === "undefined") return null;
  const v = localStorage.getItem(STORAGE_KEY);
  return v === "mobile" || v === "desktop" ? v : null;
}

function writeOverride(v) {
  if (typeof localStorage === "undefined") return;
  if (v) localStorage.setItem(STORAGE_KEY, v);
  else   localStorage.removeItem(STORAGE_KEY);
}

function autoIsMobile() {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia(MOBILE_QUERY).matches;
}

export function ViewportProvider({ children }) {
  const [override, setOverrideRaw] = useState(readOverride);
  const [autoMatch, setAutoMatch] = useState(autoIsMobile);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia(MOBILE_QUERY);
    const onChange = (e) => setAutoMatch(e.matches);
    if (mql.addEventListener) mql.addEventListener("change", onChange);
    else mql.addListener(onChange);
    setAutoMatch(mql.matches);
    return () => {
      if (mql.removeEventListener) mql.removeEventListener("change", onChange);
      else mql.removeListener(onChange);
    };
  }, []);

  const setOverride = useCallback((v) => {
    setOverrideRaw(v);
    writeOverride(v);
  }, []);

  const value = useMemo(() => {
    const isMobile = override === "mobile"
      ? true
      : override === "desktop"
        ? false
        : autoMatch;
    return { isMobile, autoMatch, override, setOverride };
  }, [override, autoMatch, setOverride]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useViewport() {
  return useContext(Ctx);
}
