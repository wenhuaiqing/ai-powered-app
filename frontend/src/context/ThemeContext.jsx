import { createContext, useContext, useState } from "react";

// Reapit visual identity — purple primary, teal AI accent, white background.
// Token shape mirrors mcnab-data-app's ThemeContext so lifted components
// (PlasmaOrb, UnifiedOrb) inherit the new palette unchanged.

export const light = {
  name: "light",
  bg: "#F6F7FA",                          // light grey section bands
  surface: "#FFFFFF",
  surfaceRaised: "#FAFBFD",
  border: "rgba(91,45,140,0.14)",
  borderBright: "rgba(91,45,140,0.34)",
  accent: "#5B2D8C",                      // primary purple
  accentGlow: "rgba(91,45,140,0.10)",
  accent2: "#0BC4B4",                     // teal — AI accent
  accent2Glow: "rgba(11,196,180,0.14)",
  text: "#0F1226",
  textMuted: "rgba(15,18,38,0.62)",
  textDim: "rgba(15,18,38,0.30)",
  sidebarBg: "#FFFFFF",
  sidebarText: "rgba(15,18,38,0.74)",
  sidebarActive: "rgba(91,45,140,0.10)",
  sidebarActiveText: "#5B2D8C",
  sidebarBorder: "rgba(91,45,140,0.10)",
  rowHover: "rgba(91,45,140,0.06)",
  rowDivider: "rgba(91,45,140,0.10)",
  groupDivider: "rgba(91,45,140,0.45)",
  gridDot: "rgba(91,45,140,0.07)",
  labelColBg: "rgba(91,45,140,0.04)",
  dot: {
    grey: "rgba(0,0,0,0.16)",
    green: "#0BC4B4",
    yellow: "#D97706",
    blue: "#5B2D8C",
    red: "#DC2626",
  },
  dotGlow: {
    green: "rgba(11,196,180,0.45)",
    yellow: "rgba(217,119,6,0.42)",
    blue: "rgba(91,45,140,0.42)",
    red: "rgba(220,38,38,0.42)",
  },
  colGroup: ["rgba(91,45,140,0.85)", "rgba(11,196,180,0.78)", "rgba(220,38,38,0.75)"],
  colGroupDim: ["rgba(91,45,140,0.07)", "rgba(11,196,180,0.07)", "rgba(220,38,38,0.06)"],
};

export const dark = {
  name: "dark",
  bg: "#0B0A14",
  surface: "#13101E",
  surfaceRaised: "#17142A",
  border: "rgba(160,120,220,0.20)",
  borderBright: "rgba(160,120,220,0.40)",
  accent: "#A57BD8",                      // lighter purple for visibility on dark
  accentGlow: "rgba(165,123,216,0.22)",
  accent2: "#1DD9C9",
  accent2Glow: "rgba(29,217,201,0.20)",
  text: "#E8E5F2",
  textMuted: "rgba(232,229,242,0.55)",
  textDim: "rgba(232,229,242,0.26)",
  sidebarBg: "#08071A",
  sidebarText: "rgba(232,229,242,0.62)",
  sidebarActive: "rgba(165,123,216,0.18)",
  sidebarActiveText: "#C9A9F5",
  sidebarBorder: "rgba(165,123,216,0.18)",
  rowHover: "rgba(165,123,216,0.08)",
  rowDivider: "rgba(165,123,216,0.16)",
  groupDivider: "rgba(165,123,216,0.50)",
  gridDot: "rgba(165,123,216,0.07)",
  labelColBg: "rgba(0,0,0,0.20)",
  dot: {
    grey: "rgba(255,255,255,0.22)",
    green: "#1DD9C9",
    yellow: "#D4A000",
    blue: "#A57BD8",
    red: "#E53935",
  },
  dotGlow: {
    green: "rgba(29,217,201,0.72)",
    yellow: "rgba(212,160,0,0.72)",
    blue: "rgba(165,123,216,0.72)",
    red: "rgba(229,57,53,0.72)",
  },
  colGroup: ["rgba(165,123,216,0.85)", "rgba(29,217,201,0.78)", "rgba(220,38,38,0.78)"],
  colGroupDim: ["rgba(165,123,216,0.10)", "rgba(29,217,201,0.08)", "rgba(220,38,38,0.08)"],
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
