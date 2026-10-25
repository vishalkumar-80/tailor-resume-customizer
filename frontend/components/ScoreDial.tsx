/** A tape-measure style ring gauge. */
export default function ScoreDial({ value, label, before, size = 132 }: { value: number; label: string; before?: number; size?: number }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const color = pct >= 75 ? "var(--ok)" : pct >= 50 ? "var(--ink)" : "var(--thread)";

  return (
    <figure className="flex flex-col items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 120 120" role="img" aria-label={`${label}: ${pct}%`}>
        {/* tick marks around the dial */}
        {Array.from({ length: 40 }).map((_, i) => {
          const a = (i / 40) * Math.PI * 2 - Math.PI / 2;
          const long = i % 5 === 0;
          const r1 = 58;
          const r2 = long ? 53.5 : 55.5;
          return (
            <line
              key={i}
              x1={60 + r1 * Math.cos(a)}
              y1={60 + r1 * Math.sin(a)}
              x2={60 + r2 * Math.cos(a)}
              y2={60 + r2 * Math.sin(a)}
              stroke="var(--ink-3)"
              strokeWidth={long ? 1.2 : 0.7}
            />
          );
        })}
        <circle cx="60" cy="60" r={r} fill="none" stroke="var(--paper-2)" strokeWidth="9" />
        {before !== undefined && (
          <circle
            cx="60"
            cy="60"
            r={r}
            fill="none"
            stroke="var(--ink-3)"
            strokeOpacity="0.35"
            strokeWidth="9"
            strokeDasharray={`${(before / 100) * c} ${c}`}
            transform="rotate(-90 60 60)"
          />
        )}
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`}
          transform="rotate(-90 60 60)"
          style={{ transition: "stroke-dasharray 1.2s cubic-bezier(.2,.8,.2,1)" }}
        />
        <text x="60" y="62" textAnchor="middle" dominantBaseline="middle" fontFamily="var(--font-instrument-serif)" fontSize="36" fill="var(--ink)">
          {pct}
          <tspan fontSize="16">%</tspan>
        </text>
      </svg>
      <figcaption className="text-center">
        <span className="block font-mono text-[11px] uppercase tracking-[0.16em] text-ink-3">{label}</span>
        {before !== undefined && (
          <span className="mt-0.5 block text-xs text-ink-2">
            was {before}%{" "}
            <span className={value - before > 0 ? "text-ok" : "text-ink-3"}>
              ({value - before >= 0 ? "+" : ""}
              {value - before})
            </span>
          </span>
        )}
      </figcaption>
    </figure>
  );
}
