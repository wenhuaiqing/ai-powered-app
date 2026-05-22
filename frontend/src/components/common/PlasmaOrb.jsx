// Lifted from mcnab-data-app/frontend/src/components/common/PlasmaOrb.jsx
// and re-skinned to the Reapit brand palette: indigo base (#4E56EA, hue 237)
// with teal (#0BAAB2, hue 183) ribbons and the brand red (#D1263D, hue 353)
// as a sparking accent. Structure is identical to the original.
import { Orb } from "react-ai-orb";

const PALETTE = {
  mainBgStart:    "hsl(237, 78%, 76%)",   // light indigo
  mainBgEnd:      "hsl(237, 62%, 28%)",   // deep indigo
  shadowColor1:   "hsla(237, 78%, 76%, 0)",
  shadowColor2:   "hsla(237, 68%, 42%, 0.5)",
  shadowColor3:   "hsla(0, 0%, 100%, 0.6)",
  shadowColor4:   "hsl(237, 60%, 34%)",
  shapeAStart:    "hsl(183, 88%, 38%)",   // teal — AI accent
  shapeAEnd:      "hsla(183, 90%, 70%, 0)",
  shapeBStart:    "hsl(237, 72%, 58%)",   // indigo
  shapeBMiddle:   "hsl(237, 60%, 36%)",
  shapeBEnd:      "hsla(237, 72%, 78%, 0)",
  shapeCStart:    "hsla(353, 70%, 92%, 0)",
  shapeCMiddle:   "hsla(353, 73%, 49%, 0.45)", // brand red flecks
  shapeCEnd:      "hsl(237, 60%, 22%)",
  shapeDStart:    "hsla(183, 50%, 92%, 0)",
  shapeDMiddle:   "hsla(183, 70%, 40%, 0.40)",
  shapeDEnd:      "hsl(237, 62%, 14%)",
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
  const color = "hsla(183, 78%, 38%, 0.55)"; // teal rings (Reapit accent2)
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
            hueRotation={237}
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
