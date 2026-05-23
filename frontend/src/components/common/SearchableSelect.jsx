// Lightweight searchable dropdown — built inline so we don't add a
// downshift/react-select dependency for the single use site (Valuations
// suburb picker). Options can be plain strings or { value, label, hint }
// objects.

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";

function normaliseOption(opt) {
  if (typeof opt === "string") return { value: opt, label: opt };
  return { value: opt.value, label: opt.label ?? opt.value, hint: opt.hint };
}

export default function SearchableSelect({
  value,
  onChange,
  options,
  placeholder = "Type to search…",
  disabled = false,
  maxItems = 60,
}) {
  const { t } = useTheme();
  const wrapRef = useRef(null);
  const inputRef = useRef(null);
  const [open, setOpen] = useState(false);
  // Filter is what the user is typing; value is the committed selection.
  const [filter, setFilter] = useState(value || "");

  // Sync filter with external value changes.
  useEffect(() => {
    setFilter(value || "");
  }, [value]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
    };
  }, [open]);

  const normalised = useMemo(
    () => (options || []).map(normaliseOption),
    [options],
  );

  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle || filter === value) return normalised.slice(0, maxItems);
    return normalised
      .filter((o) => o.label.toLowerCase().includes(needle))
      .slice(0, maxItems);
  }, [filter, value, normalised, maxItems]);

  const commit = (next) => {
    onChange?.({ target: { value: next } });
    setFilter(next);
    setOpen(false);
    inputRef.current?.blur();
  };

  const onKeyDown = (e) => {
    if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    } else if (e.key === "Enter" && open && filtered.length > 0) {
      e.preventDefault();
      commit(filtered[0].value);
    }
  };

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "0 10px 0 10px",
        background: t.bg,
        border: `1px solid ${open ? t.accent : t.border}`,
        borderRadius: 8,
        transition: "border-color .15s",
      }}>
        <Search size={13} color={t.textMuted} style={{ flexShrink: 0 }} />
        <input
          ref={inputRef}
          type="text"
          value={filter}
          onFocus={() => setOpen(true)}
          onChange={(e) => { setFilter(e.target.value); setOpen(true); }}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          style={{
            flex: 1,
            minWidth: 0,
            padding: "8px 0",
            background: "transparent",
            border: "none",
            color: t.text,
            fontSize: 13,
            fontFamily: "inherit",
            outline: "none",
          }}
        />
        <ChevronDown
          size={14}
          color={t.textMuted}
          style={{
            flexShrink: 0,
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform .15s",
            cursor: "pointer",
          }}
          onMouseDown={(e) => {
            e.preventDefault();
            setOpen((o) => !o);
            if (!open) inputRef.current?.focus();
          }}
        />
      </div>

      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 4px)",
          left: 0, right: 0,
          maxHeight: 280,
          overflowY: "auto",
          background: t.surface,
          border: `1px solid ${t.border}`,
          borderRadius: 8,
          boxShadow: "0 8px 24px rgba(15,18,38,0.10)",
          zIndex: 100,
        }}>
          {filtered.length === 0 ? (
            <div style={{ padding: "10px 12px", fontSize: 12, color: t.textMuted }}>
              No matches.
            </div>
          ) : (
            filtered.map((o) => {
              const isCurrent = o.value === value;
              return (
                <button
                  key={o.value}
                  type="button"
                  // onMouseDown.preventDefault keeps the input focused so the
                  // dropdown doesn't close before onClick fires.
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => commit(o.value)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    width: "100%",
                    padding: "7px 10px",
                    background: isCurrent ? t.accentGlow : "transparent",
                    border: "none",
                    borderBottom: `1px solid ${t.rowDivider}`,
                    color: t.text,
                    fontSize: 13,
                    fontFamily: "inherit",
                    textAlign: "left",
                    cursor: "pointer",
                    transition: "background .12s",
                  }}
                  onMouseEnter={(e) => { if (!isCurrent) e.currentTarget.style.background = t.rowHover; }}
                  onMouseLeave={(e) => { if (!isCurrent) e.currentTarget.style.background = "transparent"; }}
                >
                  {isCurrent ? <Check size={12} color={t.accent} /> : <span style={{ width: 12, flexShrink: 0 }} />}
                  <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {o.label}
                  </span>
                  {o.hint != null && (
                    <span style={{ fontSize: 11, color: t.textMuted, flexShrink: 0 }}>
                      {o.hint}
                    </span>
                  )}
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
