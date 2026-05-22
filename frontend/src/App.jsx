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
        <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
          <Routes>
            {ROUTES.map((r) => (
              <Route key={r.to} path={r.to} element={<r.component />} />
            ))}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>

      <UnifiedOrb />
    </div>
  );
}
