import { useEffect, useId, useRef, useState } from "react";

/** The shop's brass balance (world "Daripalla", SUG-59). The heavier side goes down: `left` is the cash, `right`
 *  what has to be paid. The beam swings on a damped spring and settles — the app's one authored motion — and
 *  snaps straight to rest when the phone asks for reduced motion. Pure SVG + one rAF loop, no library. */
const PIVOT = { x: 200, y: 62 };
const ARM = 140;
const MAX_TILT = 14;

export function tiltFor(left: number, right: number): number {
  const heavier = Math.max(left, right, 1);
  return Math.max(-MAX_TILT, Math.min(MAX_TILT, ((right - left) / heavier) * 30));
}

function blocks(amount: number, unit: number): number {
  return Math.max(1, Math.min(3, Math.round(amount / unit))); // three cast weights at most: the stack stays below the beam
}

function useSpring(target: number, from: number): number {
  const [angle, setAngle] = useState(from);
  const state = useRef({ a: from, v: 0 });
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      state.current = { a: target, v: 0 };
      setAngle(target);
      return;
    }
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 1 / 30);
      last = now;
      const s = state.current;
      s.v += (60 * (target - s.a) - 7 * s.v) * dt; // under-damped: one small overshoot, then rest
      s.a += s.v * dt;
      setAngle(s.a);
      if (Math.abs(target - s.a) > 0.01 || Math.abs(s.v) > 0.01) raf = requestAnimationFrame(tick);
      else setAngle(target);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return angle;
}

// the nominal masses cast into bazaar weights (বাটখারা), bottom to top — the world's detail, not data
const STAMPS = ["5", "2", "1", "1", "1"];
const BN = "০১২৩৪৫৬৭৮৯";

/** Cast iron weights: a block with shoulders, a ring handle on the top one, the mass stamped in brass. */
function Weights({ x, rimY, n, lang }: { x: number; rimY: number; n: number; lang: string }) {
  // separate same-size blocks with a gap, large enough that the stamp reads at 70 % of a 360 px phone (≥ 9 px)
  const H = 22;
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const w = 48;
        const y = rimY - H * (i + 1) + 2;
        const stamp = lang === "bn" ? STAMPS[i].replace(/\d/g, (d) => BN[Number(d)]) : STAMPS[i];
        return (
          <g key={i}>
            <path className="fill-bb-iron"
                  d={`M${x - w / 2} ${y + H - 2} V${y + 4} Q${x - w / 2} ${y + 1} ${x - w / 2 + 4} ${y + 1} H${x + w / 2 - 4} Q${x + w / 2} ${y + 1} ${x + w / 2} ${y + 4} V${y + H - 2} Z`} />
            <text x={x} y={y + 16.5} textAnchor="middle" className="fill-bb-brass font-display" fontSize={16} fontWeight={600}>
              {stamp}
            </text>
          </g>
        );
      })}
      <circle cx={x} cy={rimY - H * n - 3} r={4.5} fill="none" className="stroke-bb-iron" strokeWidth={2.5} />
    </g>
  );
}

function Pan({ hx, hy, n, grad, lang }: { hx: number; hy: number; n: number; grad: string; lang: string }) {
  const rimY = hy + 86;
  return (
    <g>
      <g className="stroke-bb-brass-deep" strokeWidth={1.5} fill="none" opacity={0.85}>
        <line x1={hx} y1={hy} x2={hx - 46} y2={rimY} />
        <line x1={hx} y1={hy} x2={hx + 46} y2={rimY} />
      </g>
      <Weights x={hx} rimY={rimY} n={n} lang={lang} />
      <path d={`M${hx - 54} ${rimY} Q${hx} ${rimY + 34} ${hx + 54} ${rimY} Z`} fill={`url(#${grad})`}
            className="stroke-bb-brass-deep" strokeWidth={1.5} />
      <circle cx={hx} cy={hy} r={4} className="fill-bb-brass-deep" />
    </g>
  );
}

export function Balance({ left, right, unit = 8000, settleFrom, className = "", label, lang = "en" }: {
  left: number; right: number; unit?: number; settleFrom?: number; className?: string; label: string; lang?: string;
}) {
  const target = tiltFor(left, right);
  const angle = useSpring(target, settleFrom ?? target);
  const grad = useId().replace(/:/g, "");
  const rad = (angle * Math.PI) / 180;
  const dx = ARM * Math.cos(rad);
  const dy = ARM * Math.sin(rad);
  return (
    <svg viewBox="0 0 400 272" role="img" aria-label={label} className={`block w-full ${className}`}>
      <defs>
        <linearGradient id={grad} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f6dc8e" />
          <stop offset="0.45" stopColor="#e2b54f" />
          <stop offset="1" stopColor="#a87a22" />
        </linearGradient>
      </defs>
      {/* counter edge and the scale's shadow on it */}
      <ellipse cx={200} cy={258} rx={150} ry={7} className="fill-bb-iron" opacity={0.18} />
      <rect x={0} y={256} width={400} height={2} className="fill-bb-iron" opacity={0.22} />
      {/* stand */}
      <rect x={196} y={PIVOT.y} width={8} height={176} fill={`url(#${grad})`} />
      <path d="M150 238 H250 L266 256 H134 Z" fill={`url(#${grad})`} className="stroke-bb-brass-deep" strokeWidth={1.5} />
      <path d={`M${PIVOT.x} ${PIVOT.y - 26} l7 10 -7 10 -7 -10 Z`} fill={`url(#${grad})`} />
      {/* beam */}
      <g transform={`rotate(${angle} ${PIVOT.x} ${PIVOT.y})`}>
        <rect x={PIVOT.x - ARM - 6} y={PIVOT.y - 5} width={2 * ARM + 12} height={10} rx={5} fill={`url(#${grad})`}
              className="stroke-bb-brass-deep" strokeWidth={1.2} />
        <rect x={PIVOT.x - 3} y={PIVOT.y - 40} width={6} height={34} className="fill-bb-iron" />
      </g>
      <circle cx={PIVOT.x} cy={PIVOT.y} r={9} fill={`url(#${grad})`} className="stroke-bb-brass-deep" strokeWidth={1.5} />
      <circle cx={PIVOT.x} cy={PIVOT.y} r={3} className="fill-bb-iron" />
      <Pan hx={PIVOT.x - dx} hy={PIVOT.y - dy} n={blocks(left, unit)} grad={grad} lang={lang} />
      <Pan hx={PIVOT.x + dx} hy={PIVOT.y + dy} n={blocks(right, unit)} grad={grad} lang={lang} />
    </svg>
  );
}

/** The logo mark: the beam and two pans, drawn small. */
export function BalanceMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={className}>
      <g className="fill-bb-brass">
        <rect x={15} y={6} width={2} height={20} />
        <rect x={4} y={7} width={24} height={2.4} rx={1.2} />
        <path d="M2 17 Q7 22 12 17 Z M20 17 Q25 22 30 17 Z" />
        <path d="M11 28 H21 L22.5 30 H9.5 Z" />
      </g>
      <g className="stroke-bb-brass" strokeWidth={0.9} fill="none">
        <path d="M7 8.5 L2.5 17 M7 8.5 L11.5 17 M25 8.5 L20.5 17 M25 8.5 L29.5 17" />
      </g>
    </svg>
  );
}
