import { Link } from "react-router-dom";
import { api, ENCODER_LABELS, fmt, type Results } from "../api";
import { useAsync } from "../useAsync";
import { ErrorNote, Section, Skeleton } from "./Card";
import { MarkerList } from "./MarkerList";
import { Disclaimer } from "./Disclaimer";
import { best, Cell, OV_NOTE, row } from "../pages/Results";

/** Designer view for a cancer with precomputed results but no computed panel (lung, colorectal, ovarian). */
export function CancerResults({ cancer, results, panelLive = false }: {
  cancer: string; results: Results | null;
  /** True when the Designer already shows this cancer's panel card and ranking above. */
  panelLive?: boolean;
}) {
  const markers = useAsync(() => api.cancerMarkers(cancer), [cancer]);
  const base = panelLive ? 3 : 1;
  const meta = results?.cancers.find((c) => c.id === cancer);
  const name = meta?.name.toLowerCase() ?? cancer;
  const hasTask = !!meta?.task;
  const f1Best = results && hasTask ? best(results, cancer, (e) => row(results, e, cancer, 1)?.macro_f1) : null;
  const cBest = results ? best(results, cancer, (e) => row(results, e, cancer, 1)?.c_index) : null;

  return (
    <div className="space-y-6">
      {!panelLive && <p role="note" className="border-l-2 border-acc pl-3 text-mute">
        <span className="text-fg">No panel computed for {name} yet.</span> The marker budget, panel card and export are
        live for breast only. Below are the precomputed {name} results{hasTask ? " and marker ranking" : ""} from the
        four-cancer run. <Link to="/results" className="underline decoration-acc underline-offset-4 hover:text-fg">all results →</Link>
      </p>}

      <div className={`grid gap-6 ${hasTask && !panelLive ? "lg:grid-cols-[1.1fr_1fr]" : ""}`}>
        <Section index={base} title={`${name} · all-model results`} id="cancer-results-title" aside="locked test set · preliminary">
          {!results ? <Skeleton h="h-48" /> : (
            <>
              <p className="mb-3 text-mute">{meta?.task ?? OV_NOTE} · survival: {meta?.survival}</p>
              <div className="relative overflow-x-auto">
                <table className="w-full">
                  <caption className="sr-only">{name} results per model on the locked test set</caption>
                  <thead>
                    <tr className="text-left text-xs text-mute">
                      <th scope="col" className="pr-3">model</th>
                      {hasTask && <th scope="col" className="pr-3">macro-F1 100% [10%]</th>}
                      <th scope="col" className="pr-3">C-index</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.encoders.map((e) => {
                      const r = row(results, e, cancer, 1);
                      return (
                        <tr key={e} className="border-t border-line align-top">
                          <th scope="row" className="py-1.5 pr-3 text-left font-normal">{ENCODER_LABELS[e] ?? e}</th>
                          {hasTask && <Cell main={fmt(r?.macro_f1)} sub={fmt(row(results, e, cancer, 0.1)?.macro_f1)}
                            ci={r?.f1_lo != null ? `${fmt(r.f1_lo)}–${fmt(r.f1_hi)}` : undefined} isBest={f1Best === e} />}
                          <Cell main={fmt(r?.c_index)} ci={r ? `${fmt(r.c_lo)}–${fmt(r.c_hi)}` : undefined} isBest={cBest === e} />
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {!hasTask && <p className="mt-3 text-[11px] text-mute">{OV_NOTE}, so there is no subtype marker ranking or panel.</p>}
            </>
          )}
        </Section>

        {hasTask && !panelLive && (
          <MarkerList markers={markers.data?.markers ?? null} k={0} error={markers.error}
            aside="ranking only · no panel" footnote={markers.data ? `${markers.data.method}.` : undefined} />
        )}
      </div>

      {hasTask && (
        <Section index={base + (panelLive ? 1 : 2)} title="known-marker check" id="cancer-known-title">
          {markers.error ? <ErrorNote error={markers.error} /> : !markers.data ? <Skeleton h="h-16" /> : !markers.data.known ? null : (
            <ul className="flex flex-wrap gap-x-6 gap-y-1">
              {Object.entries(markers.data.known.known).map(([gene, rank]) => (
                <li key={gene}><span className="text-fg">{gene}</span>{" "}
                  <span className="tabular-nums text-mute">{rank == null ? "not on the protein array" : `#${rank} of ${markers.data!.markers.length}`}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
      {!panelLive && <Disclaimer compact />}
    </div>
  );
}
