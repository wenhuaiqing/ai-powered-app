// Per-character left-to-right red sweep used to draw the eye to agent
// call-to-action copy (e.g. "Click a row to fire Valuation agent...").
// Lifted from the Dashboard hint-line implementation and packaged for
// reuse across module page headers.
//
// Each character cycles base muted -> brand red + zero-blur text-shadow
// (fake-bold to avoid layout shift) -> base muted, with a small per-char
// animation-delay so the highlight band travels left-to-right.
//
// Also exports <AgentActionHint segments=[...]/> which composes the sweep
// with inline AgentChip pieces — a Sparkles icon + heartbeat pulse on
// each named agent so the user sees up-front which specialist agents
// will fire if they click.

import { useEffect } from "react";
import { Sparkles } from "lucide-react";
import { useTheme } from "../../context/ThemeContext.jsx";

const KEYFRAME_NAME = "ai-sweep-text-char";
const KEYFRAME_AGENT_NAME = "ai-sweep-text-char-agent";
const HEARTBEAT_NAME = "ai-agent-chip-heartbeat";
const STYLE_ID = "ai-sweep-text-keyframes";

// Theme tokens are baked into the keyframes; React re-renders the <style>
// node on theme change so dark mode picks the right base colour up
// automatically. Two char-sweep keyframes:
//   normal -> base = muted text; used for surrounding hint copy.
//   agent  -> base = accent (Reapit indigo) + bold; used for the agent
//             chips so they read as indigo-bold when at rest and red
//             only during the sweep peak.
function ensureKeyframes(baseColor, peakColor, accentColor) {
  if (typeof document === "undefined") return;
  let el = document.getElementById(STYLE_ID);
  const css = `
    @keyframes ${KEYFRAME_NAME} {
      0%, 12%, 30%, 100% {
        color: ${baseColor};
        text-shadow: none;
      }
      17%, 24% {
        color: ${peakColor};
        text-shadow:
          0.4px 0 0 currentColor,
          -0.4px 0 0 currentColor,
          0 0.4px 0 currentColor,
          0 -0.4px 0 currentColor;
      }
    }
    @keyframes ${KEYFRAME_AGENT_NAME} {
      0%, 12%, 30%, 100% {
        color: ${accentColor};
        text-shadow: none;
      }
      17%, 24% {
        color: ${peakColor};
        text-shadow:
          0.4px 0 0 currentColor,
          -0.4px 0 0 currentColor,
          0 0.4px 0 currentColor,
          0 -0.4px 0 currentColor;
      }
    }
    @keyframes ${HEARTBEAT_NAME} {
      0%, 100%, 70% { transform: scale(1); }
      6%            { transform: scale(1.10); }
      12%           { transform: scale(1); }
      18%           { transform: scale(1.05); }
      24%           { transform: scale(1); }
    }
  `;
  if (!el) {
    el = document.createElement("style");
    el.id = STYLE_ID;
    document.head.appendChild(el);
  }
  if (el.textContent !== css) el.textContent = css;
}

// Per-char animated span. Stagger lets multiple text segments share one
// running sweep so the highlight band stays continuous across them.
function CharSweep({ text, startIndex = 0, cycleSec = 5, charDelay = 0.04, agent = false }) {
  const name = agent ? KEYFRAME_AGENT_NAME : KEYFRAME_NAME;
  return text.split("").map((c, i) => (
    <span
      key={i}
      aria-hidden="true"
      style={{
        animation: `${name} ${cycleSec}s linear infinite`,
        animationDelay: `${(startIndex + i) * charDelay}s`,
        whiteSpace: "pre",
      }}
    >{c}</span>
  ));
}

export default function SweepText({
  text,
  peakColor = "#D1263D",   // Reapit brand red — same as dashboard hint
  cycleSec = 5,
  charDelay = 0.04,
  style,
}) {
  const { t } = useTheme();
  const baseColor = t.textMuted;
  const accentColor = t.accent;

  useEffect(() => {
    ensureKeyframes(baseColor, peakColor, accentColor);
  }, [baseColor, peakColor, accentColor]);

  if (typeof text !== "string") return text;
  return (
    <span style={style} aria-label={text}>
      <CharSweep text={text} cycleSec={cycleSec} charDelay={charDelay} />
    </span>
  );
}

// Structured agent-action hint: a sentence built from plain text + named
// agent chips. The whole sentence cycles through the same red sweep
// (chars are staggered by their position in the full text), AND each
// agent chip gets a Sparkles icon + heartbeat scale pulse so the
// available agents are visible up-front before the user clicks.
//
// `segments` is an array of { type: "text" | "agent", value: string }.
export function AgentActionHint({
  segments,
  peakColor = "#D1263D",
  cycleSec = 5,
  charDelay = 0.04,
  heartbeatSec = 2.8,
  style,
}) {
  const { t } = useTheme();
  const baseColor = t.textMuted;
  const accentColor = t.accent;

  useEffect(() => {
    ensureKeyframes(baseColor, peakColor, accentColor);
  }, [baseColor, peakColor, accentColor]);

  if (!Array.isArray(segments) || segments.length === 0) return null;

  const fullText = segments.map((s) => s.value).join("");
  let charIdx = 0;

  return (
    <span style={style} aria-label={fullText}>
      {segments.map((seg, segIdx) => {
        const startIdx = charIdx;
        charIdx += seg.value.length;
        if (seg.type === "agent") {
          return (
            <span
              key={segIdx}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 3,
                whiteSpace: "nowrap",
                // Same rest-state styling as the "Reapit One-Platform demo"
                // chip in the dashboard hero: indigo + bold.
                fontWeight: 700,
                color: accentColor,
                animation: `${HEARTBEAT_NAME} ${heartbeatSec}s ease-in-out infinite`,
                transformOrigin: "center",
                // Treat the chip as a single typographic atom so it
                // doesn't get torn across a line break.
                verticalAlign: "baseline",
              }}
            >
              <Sparkles size={11} color={accentColor} style={{ flexShrink: 0 }} />
              {/* Wrap the char spans in a single inline-block so the
                  parent's gap:3 only applies between Sparkles and this
                  wrapper, not between every letter. */}
              <span style={{ display: "inline-block", whiteSpace: "nowrap" }}>
                <CharSweep
                  text={seg.value}
                  startIndex={startIdx}
                  cycleSec={cycleSec}
                  charDelay={charDelay}
                  agent
                />
              </span>
            </span>
          );
        }
        return (
          <span key={segIdx} aria-hidden="true">
            <CharSweep
              text={seg.value}
              startIndex={startIdx}
              cycleSec={cycleSec}
              charDelay={charDelay}
            />
          </span>
        );
      })}
    </span>
  );
}
