import { NavLink } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";

export default function SidebarNav({ routes }) {
  const { t, isDark, toggle } = useTheme();
  return (
    <aside style={{
      width: 240,
      background: t.sidebarBg,
      borderRight: `1px solid ${t.sidebarBorder}`,
      display: "flex",
      flexDirection: "column",
      padding: "20px 12px",
      gap: 4,
    }}>
      <div style={{ padding: "0 8px 18px", display: "flex", alignItems: "center", gap: 10 }}>
        <img
          src="/reapit-logo.svg"
          alt="Reapit"
          style={{
            height: 22,
            width: "auto",
            // The brand logo is already slate; invert for dark mode only.
            filter: isDark ? "brightness(0) invert(1)" : "none",
          }}
        />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1, marginLeft: 2 }}>
          <span style={{ fontSize: 10, color: t.textMuted, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            AI Platform
          </span>
          <span style={{ fontSize: 11, color: t.accent2, fontWeight: 600, letterSpacing: "0.04em" }}>
            demo
          </span>
        </div>
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {routes.map((r) => {
          const Icon = r.icon;
          return (
            <NavLink
              key={r.to}
              to={r.to}
              end={r.to === "/"}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 10px",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 500,
                color: isActive ? t.sidebarActiveText : t.sidebarText,
                background: isActive ? t.sidebarActive : "transparent",
                transition: "all .15s ease",
              })}
            >
              {Icon && <Icon size={16} strokeWidth={1.8} />}
              <span>{r.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div style={{ flex: 1 }} />

      <button
        onClick={toggle}
        style={{
          background: "none",
          border: `1px solid ${t.border}`,
          padding: "8px 10px",
          borderRadius: 8,
          color: t.textMuted,
          cursor: "pointer",
          fontSize: 12,
          fontFamily: "inherit",
        }}
      >
        {isDark ? "Light theme" : "Dark theme"}
      </button>
    </aside>
  );
}
