// Top icon strip for the mobile shell. Six module icons in a row, active
// route gets an indigo tint + 2px under-rule. The Reapit AI logo sits to
// the left as the brand mark; tapping it routes home.
import { Monitor } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useTheme } from "../../context/ThemeContext.jsx";
import { useViewport } from "../../context/ViewportContext.jsx";

export default function MobileNav({ routes }) {
  const { t, isDark } = useTheme();
  const viewport = useViewport();
  // Only offer "Desktop view" when the user is on a wide screen but has
  // forced mobile. On a real phone the desktop layout would be unusable,
  // so we hide the toggle there.
  const canShowDesktopToggle = viewport?.override === "mobile" && !viewport.autoMatch;
  return (
    <header style={{
      position: "sticky",
      top: 0,
      zIndex: 100,
      background: t.surface,
      borderBottom: `1px solid ${t.border}`,
      display: "flex",
      alignItems: "center",
      gap: 4,
      padding: "8px 10px",
      // Notch / status bar inset on iOS Safari
      paddingTop: "calc(8px + env(safe-area-inset-top, 0px))",
    }}>
      <NavLink
        to="/"
        end
        title="Rai — AppMarket co-pilot"
        aria-label="Rai home"
        style={({ isActive }) => ({
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 40,
          padding: "0 6px",
          marginRight: 2,
          background: isActive ? t.accentGlow : "transparent",
          borderRadius: 10,
          position: "relative",
          transition: "background .15s",
        })}
      >
        {({ isActive }) => (
          <>
            <img
              src="/reapit-ai-logo.svg"
              alt="Reapit AI"
              style={{
                // Logo aspect ratio is ~2.08:1, so height 16 ≈ width 33,
                // visually similar weight to the 20px module icons next to it.
                height: 16,
                width: "auto",
                filter: isDark ? "brightness(0) invert(1)" : "none",
              }}
            />
            {isActive && (
              <span style={{
                position: "absolute",
                bottom: -6,
                left: "50%",
                transform: "translateX(-50%)",
                width: 24,
                height: 2,
                background: t.accent,
                borderRadius: 2,
              }} />
            )}
          </>
        )}
      </NavLink>

      <nav style={{ flex: 1, display: "flex", gap: 2, justifyContent: canShowDesktopToggle ? "flex-start" : "space-around" }}>
        {routes.map((r) => {
          const Icon = r.icon;
          if (!Icon) return null;
          return (
            <NavLink
              key={r.to}
              to={r.to}
              end={r.to === "/"}
              title={r.label}
              aria-label={r.label}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 44,
                height: 40,
                position: "relative",
                color: isActive ? t.accent : t.textMuted,
                background: isActive ? t.accentGlow : "transparent",
                borderRadius: 10,
                transition: "background .15s, color .15s",
              })}
            >
              {({ isActive }) => (
                <>
                  <Icon size={20} strokeWidth={isActive ? 2.2 : 1.8} />
                  {isActive && (
                    <span style={{
                      position: "absolute",
                      bottom: -6,
                      left: "50%",
                      transform: "translateX(-50%)",
                      width: 24,
                      height: 2,
                      background: t.accent,
                      borderRadius: 2,
                    }} />
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {canShowDesktopToggle && (
        <button
          onClick={() => viewport.setOverride(null)}
          title="Switch back to desktop view"
          aria-label="Switch back to desktop view"
          style={{
            display: "flex", alignItems: "center", gap: 5,
            padding: "5px 9px",
            background: t.surface,
            border: `1px solid ${t.border}`,
            borderRadius: 999,
            color: t.textMuted,
            fontSize: 11,
            fontWeight: 600,
            fontFamily: "inherit",
            cursor: "pointer",
            marginLeft: 6,
            flexShrink: 0,
            transition: "border-color .15s, color .15s, background .15s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = t.accent;
            e.currentTarget.style.color = t.accent;
            e.currentTarget.style.background = t.accentGlow;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = t.border;
            e.currentTarget.style.color = t.textMuted;
            e.currentTarget.style.background = t.surface;
          }}
        >
          <Monitor size={13} strokeWidth={2} />
          Desktop
        </button>
      )}
    </header>
  );
}
