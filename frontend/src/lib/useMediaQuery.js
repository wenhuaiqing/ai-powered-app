// Tiny SSR-safe media-query hook + scroll-direction hook.
//
// `useIsMobile()` reads from ViewportContext so a user can manually override
// the auto-detected breakpoint (the "Mobile view" toggle on desktop and the
// "Desktop view" toggle in MobileNav). Auto-detect breakpoint is <=1024px so
// tablets collapse to the mobile shell.

import { useEffect, useState } from "react";
import { useViewport } from "../context/ViewportContext.jsx";

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia(query).matches;
  });
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia(query);
    const onChange = (e) => setMatches(e.matches);
    // Cross-browser: modern uses addEventListener, Safari < 14 uses addListener
    if (mql.addEventListener) mql.addEventListener("change", onChange);
    else mql.addListener(onChange);
    setMatches(mql.matches);
    return () => {
      if (mql.removeEventListener) mql.removeEventListener("change", onChange);
      else mql.removeListener(onChange);
    };
  }, [query]);
  return matches;
}

export function useIsMobile() {
  const ctx = useViewport();
  return ctx?.isMobile ?? false;
}

// Track an element's scroll direction so a docked bar can auto-hide on
// scroll-down and reveal on scroll-up. Pass either an HTMLElement ref or
// the element itself (the hook tolerates null while you wait for the ref
// to mount). Threshold ignores tiny jitters.
export function useScrollHide(scrollEl, { threshold = 8, peekAt = 16 } = {}) {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    if (!scrollEl) return;
    let lastY = scrollEl.scrollTop;
    const onScroll = () => {
      const y = scrollEl.scrollTop;
      const delta = y - lastY;
      if (Math.abs(delta) < threshold) return;
      if (y <= peekAt) setHidden(false);
      else if (delta > 0) setHidden(true);
      else setHidden(false);
      lastY = y;
    };
    scrollEl.addEventListener("scroll", onScroll, { passive: true });
    return () => scrollEl.removeEventListener("scroll", onScroll);
  }, [scrollEl, threshold, peekAt]);
  return hidden;
}
