// Lifted from mcnab-data-app/frontend/src/components/common/PlasmaOrb.jsx
// and re-skinned to Reapit purple/teal. Structure is identical so the orb
// behaviour is the same — just different hues.
import { Orb } from "react-ai-orb";

const PALETTE = {
  mainBgStart:    "hsl(282, 60%, 75%)",
  mainBgEnd:      "hsl(270, 60%, 22%)",
  shadowColor1:   "hsla(282, 60%, 75%, 0)",
  shadowColor2:   "hsla(272, 70%, 40%, 0.5)",
  shadowColor3:   "hsla(0, 0%, 100%, 0.6)",
  shadowColor4:   "hsl(272, 70%, 32%)",
  shapeAStart:    "hsl(176, 90%, 50%)",   // teal — AI accent
  shapeAEnd:      "hsla(176, 90%, 75%, 0)",
  shapeBStart:    "hsl(282, 75%, 55%)",
  shapeBMiddle:   "hsl(272, 70%, 35%)",
  shapeBEnd:      "hsla(282, 75%, 75%, 0)",
  shapeCStart:    "hsla(176, 50%, 90%, 0)",
  shapeCMiddle:   "hsla(176, 90%, 50%, 0.55)",
  shapeCEnd:      "hsl(272, 70%, 22%)",
  shapeDStart:    "hsla(282, 50%, 92%, 0)",
  shapeDMiddle:   "hsla(282, 75%, 35%, 0.45)",
  shapeDEnd:      "hsl(272, 70%, 14%)",
};

const RING_KEYFRAMES = `
  @keyframes orb-ring-cw {
    0% { transform: translate(-50%, -50%) rotate(0deg); }
    100% { transform: translate(-50%, -50%) rotate(360deg); }
  }
  @keyframes orb-ring-ccw {
    0% { transform: translate(-50%, -50%) rotate(360deg); }
    100% { transform: translate(-50%, -50%) rotate(0deg); }
  }
`;

function OrbitingRings({ size }) {
  const color = "hsla(176, 80%, 50%, 0.55)"; // teal-tinted rings
  const base = {
    position: "absolute",
    left: "50%", top: "50%",
    width: size, height: size,
    border: `2px solid ${color}`,
    pointerEvents: "none",
  };
  return (
    <>
      <div style={{ ...base, borderRadius: "38% 62% 63% 37% / 41% 44% 56% 59%", animation: "orb-ring-cw 10s linear infinite" }} />
      <div style={{ ...base, borderRadius: "41% 59% 50% 50% / 38% 62% 38% 62%", animation: "orb-ring-cw 16s linear infinite" }} />
      <div style={{ ...base, borderRadius: "50% 50% 38% 62% / 62% 38% 62% 38%", animation: "orb-ring-ccw 17s linear infinite" }} />
    </>
  );
}

export default function PlasmaOrb({ size = 56, isDark, style }) {
  const s = 54;
  const ringSize = s * 1.02;
  const outerSize = ringSize + 14;
  const offset = (outerSize - s) / 2;

  return (
    <>
      <style>{RING_KEYFRAMES}</style>
      <div style={{
        width: outerSize,
        height: outerSize,
        position: "fixed",
        bottom: 16 - offset,
        right: 16 - offset,
        zIndex: 10000,
        pointerEvents: "none",
        ...(style || {}),
      }}>
        <OrbitingRings size={ringSize} />
        <div style={{
          position: "absolute",
          left: "50%", top: "50%",
          transform: `translate(-50%, -50%) scale(${s / 200})`,
          transformOrigin: "center center",
        }}>
          <Orb
            palette={PALETTE}
            size={2}
            animationSpeedBase={0.51}
            animationSpeedHue={0.76}
            hueRotation={282}
            blobAOpacity={1}
            blobBOpacity={1}
            mainOrbHueAnimation={false}
            noShadow={false}
          />
        </div>
      </div>
    </>
  );
}
