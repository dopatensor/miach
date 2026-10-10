import type { MarkerRow } from "../api";
import { Card, ErrorNote, Skeleton } from "./Card";

export function MarkerList({ markers, k, note, error }: {
  markers: MarkerRow[] | null; k: number; note?: string; error?: string | null;
}) {
  const shown = markers?.slice(0, Math.max(k + 5, 12)) ?? [];
  const max = markers ? Math.max(...markers.map((m) => m.importance + m.importance_sd)) : 1;
  return (
    <Card title="Ranked markers" id="markers-title" shadow="#D4E2FF"
      aside={<span className="text-xs text-ink/70">top {k} in panel · next 5 shown for context</span>}>
      {error ? <ErrorNote error={error} /> : !markers ? <Skeleton h="h-64" /> : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Marker ranking by occlusion importance with bootstrap stability</caption>
              <thead>
                <tr className="text-left text-xs text-ink/70">
                  <th scope="col" className="py-1 pr-2">#</th>
                  <th scope="col" className="pr-2">Protein</th>
                  <th scope="col" className="hidden pr-2 sm:table-cell">Pathway</th>
                  <th scope="col" className="w-1/3 pr-2">Importance (± sd)</th>
                  <th scope="col" className="text-right">Stability</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((m) => {
                  const inPanel = m.rank <= k;
                  return (
                    <tr key={m.protein} className={`border-t border-ink/10 ${inPanel ? "" : "text-ink/60"}`}
                      aria-label={inPanel ? `${m.protein}, in panel` : undefined}>
                      <td className="py-1.5 pr-2 tabular-nums">{m.rank}</td>
                      <td className="pr-2">
                        <span className={inPanel ? "font-semibold" : ""}>{m.protein}</span>
                        {m.gene !== m.protein && <span className="ml-1 text-xs text-ink/60">{m.gene}</span>}
                      </td>
                      <td className="hidden pr-2 sm:table-cell"><span className={`chip ${inPanel ? "bg-sky" : "bg-white"}`}>{m.block}</span></td>
                      <td className="pr-2">
                        <div className="relative h-3 w-full rounded bg-ink/5" title={`${m.importance.toFixed(3)} ± ${m.importance_sd.toFixed(3)}`}>
                          <div className={`absolute h-3 rounded ${inPanel ? "bg-navy" : "bg-ink/30"}`}
                            style={{ width: `${Math.max(0, (m.importance / max) * 100)}%` }} />
                          <div className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-coral"
                            style={{
                              left: `${Math.max(0, ((m.importance - m.importance_sd) / max) * 100)}%`,
                              width: `${((2 * m.importance_sd) / max) * 100}%`,
                            }} />
                        </div>
                      </td>
                      <td className="text-right tabular-nums">{Math.round(m.stability * 100)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-ink/70">
            Stability = share of 20 bootstrap refits that put the protein in the top 8. {note}
          </p>
        </>
      )}
    </Card>
  );
}
