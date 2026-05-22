import { Route, Routes, Navigate } from "react-router-dom";
import HeaderBar from "./components/common/HeaderBar.jsx";
import SidebarNav from "./components/common/SidebarNav.jsx";
import UnifiedOrb from "./components/common/UnifiedOrb.jsx";
import { useTheme } from "./context/ThemeContext.jsx";
import { getRoutes } from "./navigation.js";

const ROUTES = getRoutes();

export default function App() {
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
