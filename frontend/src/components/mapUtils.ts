import type { LatentPoint } from "../api";
import { SUBTYPES } from "../api";

const med = (v: number[]) => { const s = [...v].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };

/** Median position of each subtype's training patients, used to write subtype names on the map.
 *  Labels closer than `minGap` (in x units) alternate above/below so they don't collide. */
export function centroids(points: LatentPoint[], minGap = 0) {
  const cs = SUBTYPES.map((s) => {
    const pts = points.filter((p) => p.subtype === s && p.split === "train");
    return pts.length ? { subtype: s, x: med(pts.map((p) => p.x)), y: med(pts.map((p) => p.y)), dy: -10 } : null;
  }).filter((c): c is { subtype: (typeof SUBTYPES)[number]; x: number; y: number; dy: number } => c !== null)
    .sort((a, b) => a.x - b.x);
  cs.forEach((c, i) => { if (i > 0 && c.x - cs[i - 1].x < minGap && cs[i - 1].dy < 0) c.dy = 20; });
  return cs;
}

/** Central range of a coordinate (drops the most extreme 1% each side) so outliers don't squash the map. */
export function domain(v: number[], f = 0.01): [number, number] {
  const s = [...v].sort((a, b) => a - b);
  const lo = s[Math.floor(f * (s.length - 1))], hi = s[Math.ceil((1 - f) * (s.length - 1))];
  const pad = (hi - lo) * 0.04;
  return [Math.floor(lo - pad), Math.ceil(hi + pad)];
}
