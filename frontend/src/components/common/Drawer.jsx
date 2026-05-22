// Shared side drawer used by Properties + Pipeline list rows.
// Slides in from the right, click-outside closes, ESC closes.

import { useEffect } from "react";
import { X } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";

const STYLE_ID = "drawer-keyframes";
function ensureKeyframes() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
    @keyframes dr-slideIn  { from { transform: translateX(100%); } to { transform: translateX(0); } }
    @keyframes dr-fadeIn   { from { opacity: 0; } to { opacity: 1; } }
  `;
  document.head.appendChild(s);
}

export default function Drawer({ open, onClose, title, subtitle, children, width = 480 }) {
  const { t, isDark } = useTheme();

  useEffect(() => { ensureKeyframes(); }, []);
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 9990,
          background: "rgba(15,18,38,0.32)", backdropFilter: "blur(2px)",
          animation: "dr-fadeIn .15s ease forwards",
        }}
      />
      <aside
        style={{
          position: "fixed",
          top: 0, bottom: 0, right: 0,
          width,
          maxWidth: "92vw",
          zIndex: 9991,
          background: isDark ? "rgba(13,10,28,0.99)" : t.surface,
          borderLeft: `1px solid ${t.border}`,
          boxShadow: isDark
            ? "-8px 0 32px rgba(0,0,0,0.6)"
            : "-8px 0 32px rgba(15,18,38,0.12)",
          display: "flex",
          flexDirection: "column",
          animation: "dr-slideIn .2s cubic-bezier(0.4,0,0.2,1) forwards",
        }}
      >
        <div style={{
          padding: "16px 20px 12px",
          borderBottom: `1px solid ${t.border}`,
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
        }}>
          <div style={{ flex: 1, lineHeight: 1.2 }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: t.text }}>{title}</div>
            {subtitle && (
              <div style={{ fontSize: 12, color: t.textMuted, marginTop: 4 }}>{subtitle}</div>
            )}
          </div>
          <button
            onClick={onClose}
            title="Close (Esc)"
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: 6, borderRadius: 6, color: t.textMuted,
              display: "flex", alignItems: "center",
            }}
          >
            <X size={18} />
          </button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {children}
        </div>
      </aside>
    </>
  );
}
