import { Smartphone } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useViewport } from "../../context/ViewportContext.jsx";

export default function HeaderBar({ routes }) {
  const { t } = useTheme();
  const viewport = useViewport();
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
      <button
        onClick={() => viewport?.setOverride("mobile")}
        title="Preview the mobile layout"
        aria-label="Switch to mobile view"
        style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "5px 11px 5px 9px",
          background: t.surface,
          border: `1px solid ${t.border}`,
          borderRadius: 999,
          color: t.textMuted,
          fontSize: 11,
          fontWeight: 600,
          fontFamily: "inherit",
          cursor: "pointer",
          transformOrigin: "center",
          // Heartbeat scale loop (mirrors the dashboard RAI logo pulse)
          // gently nudges the pill so it reads as the call-to-action.
          animation: "mv-heartbeat 3.6s ease-in-out infinite",
          transition: "border-color .15s, background .15s",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "#D1263D";
          e.currentTarget.style.background = "rgba(209,38,61,0.10)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = t.border;
          e.currentTarget.style.background = t.surface;
        }}
      >
        <Smartphone size={13} strokeWidth={2} />
        <span style={{ display: "inline-block", whiteSpace: "nowrap" }}>
          {"Mobile view".split("").map((c, i) => (
            <span
              key={i}
              style={{
                animation: "mv-char-sweep 4s linear infinite",
                animationDelay: `${i * 0.04}s`,
                whiteSpace: "pre",
              }}
            >{c}</span>
          ))}
        </span>
      </button>
      <style>{`
        @keyframes mv-char-sweep {
          0%, 12%, 30%, 100% {
            color: ${t.textMuted};
            text-shadow: none;
          }
          17%, 24% {
            color: #D1263D;
            text-shadow:
              0.4px 0 0 currentColor,
              -0.4px 0 0 currentColor,
              0 0.4px 0 currentColor,
              0 -0.4px 0 currentColor;
          }
        }
        @keyframes mv-heartbeat {
          0%, 100%, 70% { transform: scale(1); }
          6%            { transform: scale(1.10); }
          12%           { transform: scale(1); }
          18%           { transform: scale(1.05); }
          24%           { transform: scale(1); }
        }
      `}</style>
    </header>
  );
}
