import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";

export default function ToolCallCard({ node, tool, args, preview }) {
  const { t } = useTheme();
  const [open, setOpen] = useState(false);
  const argSummary = args ? truncate(JSON.stringify(args), 80) : null;
  return (
    <div style={{
      background: t.surfaceRaised,
      border: `1px solid ${t.border}`,
      borderRadius: 8,
      padding: "8px 10px",
      fontSize: 12,
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          cursor: argSummary ? "pointer" : "default",
          display: "flex",
          alignItems: "center",
          gap: 6,
          color: t.textMuted,
          fontFamily: "inherit",
          fontSize: 12,
        }}
      >
        {argSummary && (open ? <ChevronDown size={12} /> : <ChevronRight size={12} />)}
        <span style={{ fontWeight: 600, color: t.text }}>{tool}</span>
        {preview && <span style={{ color: t.textMuted }}>· {preview}</span>}
      </button>
      {open && argSummary && (
        <pre style={{
          margin: "6px 0 0",
          padding: "6px 8px",
          fontSize: 11,
          background: t.labelColBg,
          border: `1px solid ${t.border}`,
          borderRadius: 6,
          color: t.textMuted,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          fontFamily: "ui-monospace, Menlo, monospace",
        }}>{JSON.stringify(args, null, 2)}</pre>
      )}
    </div>
  );
}

function truncate(s, n) {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + "…";
}
