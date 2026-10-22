import type { Panel } from "../api";
import { fmt } from "../api";
import { ErrorNote, Section, Skeleton, TestSetTag } from "./Card";
import { Disclaimer } from "./Disclaimer";
import { BudgetCurve } from "./BudgetCurve";

export function PanelCard({ panel, error, costPerMarker, curve, onPickK }: {
  panel: Panel | null; error?: string | null; costPerMarker?: number | null;
  curve?: { k: number; f1: number }[]; onPickK?: (k: number) => void;
}) {
  const title = panel ? `candidate panel · ${panel.k} marker${panel.k > 1 ? "s" : ""}` : "candidate panel";
  return (
    <Section index={1} title={title} id="panel-title" aside={<TestSetTag n={panel?.test_n} />}>
      {error ? <ErrorNote error={error} /> : !panel ? <Skeleton h="h-56" /> : (
        <div className="space-y-5" aria-live="polite">
          <ul className="flex flex-wrap gap-1.5" aria-label="Panel markers">
            {panel.marker_details.map((m) => <li key={m.protein} className="chip font-mono">{m.protein}</li>)}
          </ul>
          <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
            <div>
              <div className="label">{panel.goal === "survival" ? `c-index (${panel.survival_endpoint.toLowerCase()})` : "macro-f1"}</div>
              <div className="mt-1 text-7xl font-bold leading-none tracking-tight text-acc tabular-nums font-sans">
                {fmt(panel.goal === "survival" ? panel.metrics.c_index : panel.metrics.macro_f1)}
              </div>
            </div>
            <Retained panel={panel} />
          </div>
          <dl className="grid grid-cols-3 gap-3 border-t border-line pt-4">
            {(panel.goal === "survival"
              ? [["macro-f1", "macro_f1"], ["bal. acc", "balanced_acc"], ["auroc", "auroc"]] as const
              : [["bal. acc", "balanced_acc"], ["auroc", "auroc"], ["c-index", "c_index"]] as const
            ).map(([label, key]) => (
              <div key={key}>
                <dt className="label">{label}</dt>
                <dd className="mt-1 text-2xl tabular-nums">{fmt(panel.metrics[key])}</dd>
                <dd className="text-xs text-mute">all {panel.full_model.k}: {fmt(panel.full_model.metrics[key])}</dd>
              </div>
            ))}
          </dl>
          {curve && curve.length > 1 && (
            <div className="no-print border-t border-line pt-4">
              <BudgetCurve points={curve} full={panel.full_model.metrics.macro_f1} k={panel.k} onPick={onPickK} />
            </div>
          )}
          {panel.note && <p className="rounded-lg border-l-2 border-acc bg-accsoft px-3 py-2 text-mute">{panel.note}</p>}
          {costPerMarker != null && costPerMarker > 0 && (
            <p>cost per test: <span className="tabular-nums">{(costPerMarker * panel.k).toFixed(2)}</span>
              <span className="text-mute"> = {panel.k} × {costPerMarker.toFixed(2)}</span></p>
          )}
          <details className="text-xs text-mute">
            <summary className="cursor-pointer hover:text-fg">how these numbers were made</summary>
            <p className="mt-1">{panel.method}. Subtype metrics use the {panel.test_labelled} test patients with a {panel.label_name}.</p>
            <p className="mt-1">{panel.c_index_note}. {panel.test_events} {panel.event_word} events in the test set.</p>
          </details>
          <Disclaimer compact />
        </div>
      )}
    </Section>
  );
}

function Retained({ panel }: { panel: Panel }) {
  const pct = (panel.metrics.macro_f1 / panel.full_model.metrics.macro_f1) * 100;
  return (
    <p className="pb-1 text-mute">
      vs {fmt(panel.full_model.metrics.macro_f1)} with all {panel.full_model.k} proteins
      <br /><span className="text-fg">{pct.toFixed(0)}%</span> of full-model macro-f1 with {panel.k} of {panel.full_model.k} proteins
    </p>
  );
}
