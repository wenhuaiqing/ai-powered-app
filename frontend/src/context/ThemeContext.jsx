import { createContext, useContext, useState } from "react";

// Reapit brand palette confirmed against reapit.com.au CTAs and the logo:
//   #4E56EA  indigo  — primary CTA / buttons / arrows / active states
//   #4A5A6B  slate   — wordmark text (used by the logo SVG itself)
//   #0BAAB2  teal    — AI accent (darkened sibling of logomark #98C1C2)
//   #D1263D  red     — emphasis / alert
//   #FD9E1D  orange  — warm channel (warnings, yellow series)
// Token shape mirrors mcnab-data-app's ThemeContext so lifted components
// (PlasmaOrb, UnifiedOrb) inherit the palette unchanged.

export const light = {
  name: "light",
  bg: "#F4F6FB",                          // soft indigo-tinted grey
  surface: "#FFFFFF",
  surfaceRaised: "#FAFBFE",
  border: "rgba(78,86,234,0.16)",
  borderBright: "rgba(78,86,234,0.34)",
  accent: "#4E56EA",                      // Reapit primary indigo
  accentGlow: "rgba(78,86,234,0.10)",
  accent2: "#0BAAB2",                     // teal — AI accent
  accent2Glow: "rgba(11,170,178,0.16)",
  text: "#171A2E",                        // near-black indigo
  textMuted: "rgba(23,26,46,0.62)",
  textDim: "rgba(23,26,46,0.30)",
  sidebarBg: "#FFFFFF",
  sidebarText: "rgba(23,26,46,0.74)",
  sidebarActive: "rgba(78,86,234,0.10)",
  sidebarActiveText: "#4E56EA",
  sidebarBorder: "rgba(78,86,234,0.10)",
  rowHover: "rgba(78,86,234,0.06)",
  rowDivider: "rgba(78,86,234,0.10)",
  groupDivider: "rgba(78,86,234,0.45)",
  gridDot: "rgba(78,86,234,0.07)",
  labelColBg: "rgba(78,86,234,0.04)",
  dot: {
    grey: "rgba(23,26,46,0.18)",
    green: "#0BAAB2",                     // teal
    yellow: "#FD9E1D",                    // brand orange
    blue: "#4E56EA",                      // brand indigo
    red: "#D1263D",                       // brand red
  },
  dotGlow: {
    green: "rgba(11,170,178,0.45)",
    yellow: "rgba(253,158,29,0.42)",
    blue: "rgba(78,86,234,0.42)",
    red: "rgba(209,38,61,0.42)",
  },
  colGroup: ["rgba(78,86,234,0.88)", "rgba(11,170,178,0.80)", "rgba(209,38,61,0.78)"],
  colGroupDim: ["rgba(78,86,234,0.07)", "rgba(11,170,178,0.07)", "rgba(209,38,61,0.06)"],
};

export const dark = {
  name: "dark",
  bg: "#0E1024",
  surface: "#161A33",
  surfaceRaised: "#1B2040",
  border: "rgba(150,158,250,0.20)",
  borderBright: "rgba(150,158,250,0.38)",
  accent: "#8A91F2",                      // lighter indigo for dark-mode visibility
  accentGlow: "rgba(138,145,242,0.22)",
  accent2: "#2BD3D5",                     // teal popped up for dark bg
  accent2Glow: "rgba(43,211,213,0.20)",
  text: "#E8EAF6",
  textMuted: "rgba(232,234,246,0.55)",
  textDim: "rgba(232,234,246,0.28)",
  sidebarBg: "#0A0C1F",
  sidebarText: "rgba(232,234,246,0.62)",
  sidebarActive: "rgba(138,145,242,0.18)",
  sidebarActiveText: "#C8CCF8",
  sidebarBorder: "rgba(138,145,242,0.18)",
  rowHover: "rgba(138,145,242,0.08)",
  rowDivider: "rgba(138,145,242,0.16)",
  groupDivider: "rgba(138,145,242,0.50)",
  gridDot: "rgba(138,145,242,0.07)",
  labelColBg: "rgba(0,0,0,0.22)",
  dot: {
    grey: "rgba(255,255,255,0.22)",
    green: "#2BD3D5",
    yellow: "#FFB54C",
    blue: "#8A91F2",
    red: "#E64A60",
  },
  dotGlow: {
    green: "rgba(43,211,213,0.72)",
    yellow: "rgba(255,181,76,0.72)",
    blue: "rgba(138,145,242,0.72)",
    red: "rgba(230,74,96,0.72)",
  },
  colGroup: ["rgba(138,145,242,0.88)", "rgba(43,211,213,0.80)", "rgba(230,74,96,0.78)"],
  colGroupDim: ["rgba(138,145,242,0.10)", "rgba(43,211,213,0.08)", "rgba(230,74,96,0.08)"],
};

const Ctx = createContext(null);

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(false);
  return (
    <Ctx.Provider value={{ t: isDark ? dark : light, isDark, toggle: () => setIsDark(v => !v) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useTheme() {
  return useContext(Ctx);
}
