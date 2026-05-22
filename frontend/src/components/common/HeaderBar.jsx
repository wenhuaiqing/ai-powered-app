import { useLocation } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";

export default function HeaderBar({ routes }) {
  const { t } = useTheme();
  const location = useLocation();
  const current = routes.find((r) => r.to === location.pathname) || routes[0];

  return (
    <header style={{
      height: 56,
      borderBottom: `1px solid ${t.border}`,
      background: t.surface,
      display: "flex",
      alignItems: "center",
      padding: "0 24px",
      gap: 16,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {current?.icon && <current.icon size={18} color={t.accent} strokeWidth={2} />}
        <span style={{ fontSize: 16, fontWeight: 600, color: t.text, letterSpacing: "-0.005em" }}>
          {current?.label || "Dashboard"}
        </span>
      </div>
      <div style={{ flex: 1 }} />
      <div style={{
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        padding: "4px 9px",
        borderRadius: 999,
        background: t.accent2Glow,
        color: t.accent2,
      }}>
        AI Powered
      </div>
    </header>
  );
}
