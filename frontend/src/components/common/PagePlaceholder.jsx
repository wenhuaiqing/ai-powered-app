import { useTheme } from "../../context/ThemeContext.jsx";

export default function PagePlaceholder({ title, hint }) {
  const { t } = useTheme();
  return (
    <div style={{
      maxWidth: 720,
      padding: "28px 32px",
      background: t.surface,
      border: `1px dashed ${t.border}`,
      borderRadius: 12,
    }}>
      <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 600, color: t.text }}>{title}</h2>
      <p style={{ margin: 0, fontSize: 13, color: t.textMuted, lineHeight: 1.6 }}>
        {hint || "This module ships in Day 4. The AppMarket co-pilot in the bottom-right already works on this page — try it now."}
      </p>
    </div>
  );
}
