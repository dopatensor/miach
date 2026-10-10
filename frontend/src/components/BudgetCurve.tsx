import { useState } from "react";

const W = 600, H = 120, PAD = { l: 28, r: 8, t: 8, b: 18 };

/** Macro-F1 of the precomputed panel at every budget k, with the full-model line. Click to pick k. */
export function BudgetCurve({ points, full, k, onPick }: {
  points: { k: number; f1: number }[]; full: number; k: number; onPick?: (k: number) => void;
}) {
  const [hover, setHover] = useState<number | null>(null);
  if (points.length < 2) return null;
  const kMax = points[points.length - 1].k;
  const yMax = Math.max(full, ...points.map((p) => p.f1)) + 0.05;
  const x = (kk: number) => PAD.l + ((kk - 1) / (kMax - 1)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v / yMax) * (H - PAD.t - PAD.b);
  const path = points.map((p, i) => `${i ? "L" : "M"}${x(p.k).toFixed(1)},${y(p.f1).toFixed(1)}`).join("");
  const shown = hover ?? k;
  const cur = points.find((p) => p.k === shown);
  const pick = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    return Math.min(kMax, Math.max(1, Math.round(((px - PAD.l) / (W - PAD.l - PAD.r)) * (kMax - 1) + 1)));
  };
  return (
    <figure>
      <figcaption className="mb-1 flex justify-between text-[11px] text-mute">
        <span>macro-f1 by marker budget</span>
        <span className="tabular-nums">{cur && <>k = {cur.k} · <span className="text-fg">{cur.f1.toFixed(2)}</span></>}</span>
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full cursor-crosshair select-none" role="img"
        aria-label={`Macro-F1 for panels of 1 to ${kMax} markers; full model ${full.toFixed(2)}.`}
        onMouseMove={(e) => setHover(pick(e))} onMouseLeave={() => setHover(null)}
        onClick={(e) => onPick?.(pick(e))}>
        {[0, 0.25, 0.5].filter((v) => v < yMax).map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeWidth={1} />
            <text x={PAD.l - 6} y={y(v) + 3} textAnchor="end" fontSize={9} fill="var(--mute)">{v.toFixed(2)}</text>
          </g>
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={y(full)} y2={y(full)} stroke="var(--mute)" strokeDasharray="3 4" />
        <text x={W - PAD.r} y={y(full) - 4} textAnchor="end" fontSize={9} fill="var(--mute)">all 198 · {full.toFixed(2)}</text>
        <path d={path} fill="none" stroke="var(--fg)" strokeWidth={1.5} strokeLinejoin="round" />
        {[1, 10, 20, 30].filter((t) => t <= kMax).map((t) => (
          <text key={t} x={x(t)} y={H - 4} textAnchor="middle" fontSize={9} fill="var(--mute)">{t}</text>
        ))}
        {cur && (
          <g>
            <line x1={x(cur.k)} x2={x(cur.k)} y1={PAD.t} y2={H - PAD.b} stroke={hover ? "var(--mute)" : "var(--acc)"} strokeWidth={1} />
            <rect x={x(cur.k) - 3.5} y={y(cur.f1) - 3.5} width={7} height={7} fill="var(--acc)" />
          </g>
        )}
      </svg>
    </figure>
  );
}
