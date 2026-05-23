import { useState } from "react";
import { Route, Routes, Navigate, useLocation } from "react-router-dom";
import HeaderBar from "./components/common/HeaderBar.jsx";
import MobileNav from "./components/common/MobileNav.jsx";
import SidebarNav from "./components/common/SidebarNav.jsx";
import UnifiedOrb from "./components/common/UnifiedOrb.jsx";
import { useTheme } from "./context/ThemeContext.jsx";
import { useIsMobile, useScrollHide } from "./lib/useMediaQuery.js";
import { getRoutes } from "./navigation.js";

const ROUTES = getRoutes();

export default function App() {
  const isMobile = useIsMobile();
  return isMobile ? <MobileShell /> : <DesktopShell />;
}

function DesktopShell() {
  const { t } = useTheme();
  return (
    <div style={{
      display: "flex",
      height: "100vh",
      background: t.bg,
      color: t.text,
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <SidebarNav routes={ROUTES} />

      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <HeaderBar routes={ROUTES} />
        {/* The scroll container intentionally has no padding so that sticky
            children (e.g. Properties / Pipeline table headers) anchor flush
            against the visible top of the scroll viewport. Padding lives on
            the inner div so every page still gets the 24/28 inset. */}
        <div style={{ flex: 1, overflow: "auto" }}>
          <div style={{ padding: "24px 28px" }}>
            <Routes>
              {ROUTES.map((r) => (
                <Route key={r.to} path={r.to} element={<r.component />} />
              ))}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </div>
      </main>

      <UnifiedOrb />
    </div>
  );
}

// Mobile shell: top icon strip + body. On "/" Rai takes the full body
// (Dashboard skipped). On any other route the module page renders and Rai
// shrinks to a docked input bar (auto-hides on scroll-down — wired in
// Phase A.5), expanding back into a 90dvh bottom sheet on tap.
function MobileShell() {
  const { t } = useTheme();
  const location = useLocation();
  const isHome = location.pathname === "/";
  const [scrollEl, setScrollEl] = useState(null);
  const dockedHidden = useScrollHide(scrollEl);
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100dvh",
      background: t.bg,
      color: t.text,
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <MobileNav routes={ROUTES} />

      <main style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, position: "relative" }}>
        {isHome ? (
          // Home becomes Rai full-page — module Dashboard is skipped on
          // mobile per spec ("orb window becomes the homepage of the app").
          <UnifiedOrb />
        ) : (
          <>
            <div ref={setScrollEl} style={{ flex: 1, overflow: "auto" }}>
              <div style={{
                // Leave room for the docked Rai bar (~52px) + safe-area inset.
                padding: "16px 14px calc(80px + env(safe-area-inset-bottom, 0px))",
              }}>
                <Routes>
                  {ROUTES.map((r) => (
                    <Route key={r.to} path={r.to} element={<r.component />} />
                  ))}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </div>
            </div>
            <UnifiedOrb dockedHidden={dockedHidden} />
          </>
        )}
      </main>
    </div>
  );
}
