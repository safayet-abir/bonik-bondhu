/** Small authored scenes from the bazaar counter (world "Daripalla"). Inline SVG in the world's inks only;
 *  the ledger writes itself in once (CSS stroke animation, off for reduced motion). */
export function LedgerScene({ className = "" }: { className?: string }) {
  const rows = [52, 62, 72, 82];
  return (
    <svg viewBox="0 0 320 120" aria-hidden className={`block w-full ${className}`}>
      {/* counter */}
      <rect x={0} y={100} width={320} height={20} className="fill-bb-iron" opacity={0.28} />
      <rect x={0} y={99} width={320} height={2} className="fill-bb-brass" opacity={0.7} />
      {/* open ledger: iron cover, enamel pages, spine */}
      <path d="M48 44 L160 38 L272 44 L276 100 L160 96 L44 100 Z" className="fill-bb-iron" />
      <path d="M54 46 L158 41 L158 92 L50 96 Z" className="fill-bb-enamel" />
      <path d="M162 41 L266 46 L270 96 L162 92 Z" className="fill-bb-enamel" />
      <line x1={160} y1={40} x2={160} y2={95} className="stroke-bb-iron" strokeWidth={2} opacity={0.4} />
      {/* the entries write themselves in */}
      <g className="stroke-bb-wall" strokeWidth={2.5} strokeLinecap="round" fill="none">
        {rows.map((y, i) => (
          <line key={y} x1={64} y1={y} x2={i === 3 ? 120 : 146} y2={y - 2} pathLength={100}
                className="bb-write" style={{ animationDelay: `${250 + i * 180}ms` }} />
        ))}
        {rows.slice(0, 3).map((y, i) => (
          <line key={`r${y}`} x1={176} y1={y - 1} x2={252} y2={y + 1} pathLength={100}
                className="bb-write" style={{ animationDelay: `${980 + i * 180}ms` }} />
        ))}
      </g>
      <line x1={176} y1={84} x2={252} y2={86} className="stroke-bb-brass-deep bb-write" strokeWidth={3}
            pathLength={100} style={{ animationDelay: "1560ms" }} />
      {/* pen and a stack of coins */}
      <line x1={238} y1={94} x2={292} y2={60} className="stroke-bb-brass" strokeWidth={5} strokeLinecap="round" />
      {[0, 1, 2].map((i) => (
        <ellipse key={i} cx={28} cy={94 - i * 7} rx={16} ry={5} className="fill-bb-brass stroke-bb-brass-deep" strokeWidth={1.2} />
      ))}
    </svg>
  );
}
