// Shared detail surface used by Properties + Pipeline list rows.
// Desktop: slides in from the right as a side drawer.
// Mobile (<=1024px): slides up from the bottom as a full-height sheet,
// matching the Rai bottom-sheet pattern so the platform feels consistent.

import { useEffect } from "react";
import { X } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useIsMobile } from "../../lib/useMediaQuery.js";

const STYLE_ID = "drawer-keyframes";
function ensureKeyframes() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = `
    @keyframes dr-slideIn  { from { transform: translateX(100%); } to { transform: translateX(0); } }
    @keyframes dr-slideUp  { from { transform: translateY(100%); } to { transform: translateY(0); } }
    @keyframes dr-fadeIn   { from { opacity: 0; } to { opacity: 1; } }
  `;
  document.head.appendChild(s);
}

export default function Drawer({ open, onClose, title, subtitle, children, width = 480 }) {
  const { t, isDark } = useTheme();
  const isMobile = useIsMobile();

  useEffect(() => { ensureKeyframes(); }, []);
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const desktopFrame = {
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
  };

  const mobileFrame = {
    position: "fixed",
    left: 0, right: 0, bottom: 0,
    top: 0,                                     // full height — same as Rai sheet at 100dvh
    zIndex: 9991,
    background: isDark ? "rgba(13,10,28,0.99)" : t.surface,
    boxShadow: isDark
      ? "0 -8px 32px rgba(0,0,0,0.6)"
      : "0 -8px 32px rgba(15,18,38,0.12)",
    display: "flex",
    flexDirection: "column",
    animation: "dr-slideUp .22s cubic-bezier(0.4,0,0.2,1) forwards",
    paddingBottom: "env(safe-area-inset-bottom, 0px)",
  };

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
      <aside style={isMobile ? mobileFrame : desktopFrame}>
        {/* Mobile drag-handle pip so the sheet visually reads as draggable */}
        {isMobile && (
          <div style={{
            paddingTop: "calc(8px + env(safe-area-inset-top, 0px))",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}>
            <span style={{
              width: 38, height: 4, borderRadius: 2,
              background: t.border,
            }} />
          </div>
        )}
        <div style={{
          padding: isMobile ? "10px 16px 10px" : "16px 20px 12px",
          borderBottom: `1px solid ${t.border}`,
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
          flexShrink: 0,
        }}>
          <div style={{ flex: 1, lineHeight: 1.2, minWidth: 0 }}>
            <div style={{
              fontSize: 16, fontWeight: 600, color: t.text,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>{title}</div>
            {subtitle && (
              <div style={{ fontSize: 12, color: t.textMuted, marginTop: 4 }}>{subtitle}</div>
            )}
          </div>
          <button
            onClick={onClose}
            title="Close (Esc)"
            aria-label="Close"
            style={{
              background: "none", border: "none", cursor: "pointer",
              padding: 6, borderRadius: 6, color: t.textMuted,
              display: "flex", alignItems: "center", flexShrink: 0,
            }}
          >
            <X size={18} />
          </button>
        </div>
        <div style={{
          flex: 1, overflowY: "auto",
          padding: isMobile ? "16px 16px 24px" : "16px 20px",
        }}>
          {children}
        </div>
      </aside>
    </>
  );
}
