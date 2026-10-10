import type { MarkerRow } from "../api";
import { ErrorNote, Section, Skeleton } from "./Card";

export function MarkerList({ markers, k, note, error }: {
  markers: MarkerRow[] | null; k: number; note?: string; error?: string | null;
}) {
  const shown = markers?.slice(0, Math.max(k + 3, 10)) ?? [];
  const max = markers ? Math.max(...markers.map((m) => m.importance)) : 1;
  return (
    <Section index={2} title="ranked markers" id="markers-title" aside={`top ${k} in panel`}>
      {error ? <ErrorNote error={error} /> : !markers ? <Skeleton h="h-64" /> : (
        <>
          <table className="w-full">
            <caption className="sr-only">Marker ranking by occlusion importance with bootstrap stability</caption>
            <thead>
              <tr className="text-left text-[11px] text-mute">
                <th scope="col" className="w-8 pb-2 font-normal">#</th>
                <th scope="col" className="pb-2 font-normal">protein</th>
                <th scope="col" className="hidden pb-2 font-normal sm:table-cell">pathway</th>
                <th scope="col" className="w-1/4 pb-2 font-normal">importance</th>
                <th scope="col" className="pb-2 text-right font-normal">stab.</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((m) => {
                const inPanel = m.rank <= k;
                return (
                  <tr key={m.protein} className={`border-t border-line ${inPanel ? "" : "text-mute"}`}>
                    <td className="py-1.5 tabular-nums">{m.rank}</td>
                    <td>{m.protein}</td>
                    <td className="hidden text-mute sm:table-cell">{m.block.toLowerCase()}</td>
                    <td>
                      <div className="h-px w-full bg-line" title={`${m.importance.toFixed(3)} ± ${m.importance_sd.toFixed(3)}`}>
                        <div className="h-px" style={{ width: `${Math.max(0, (m.importance / max) * 100)}%`, background: inPanel ? "var(--fg)" : "var(--mute)", height: "3px", marginTop: "-1px" }} />
                      </div>
                    </td>
                    <td className="text-right tabular-nums">{Math.round(m.stability * 100)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-[11px] text-mute">stability = share of 20 bootstrap refits with the protein in the top 8. {note}</p>
        </>
      )}
    </Section>
  );
}
