import type { Panel } from "../api";
import { fmt } from "../api";
import { Card, ErrorNote, Skeleton } from "./Card";
import { Disclaimer } from "./Disclaimer";

export function PanelCard({ panel, error, costPerMarker }: {
  panel: Panel | null; error?: string | null; costPerMarker?: number | null;
}) {
  return (
    <Card title={panel ? `Candidate panel · ${panel.k} marker${panel.k > 1 ? "s" : ""}` : "Candidate panel"}
      id="panel-title" shadow="#EEE772" className="border-[3px]"
      aside={<span className="chip bg-sun">Locked test set · n = {panel?.test_n ?? 176} · preliminary</span>}>
      {error ? <ErrorNote error={error} /> : !panel ? <Skeleton h="h-48" /> : (
        <div className="space-y-4" aria-live="polite">
          <ul className="flex flex-wrap gap-2" aria-label="Panel markers">
            {panel.marker_details.map((m) => (
              <li key={m.protein} className="chip bg-sky text-sm">
                {m.protein}{m.gene && m.gene !== m.protein && <span className="text-ink/60"> {m.gene}</span>}
              </li>
            ))}
          </ul>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Metric label="Macro-F1" value={panel.metrics.macro_f1} full={panel.full_model.metrics.macro_f1}
              highlight={panel.goal === "subtype"} />
            <Metric label="Balanced accuracy" value={panel.metrics.balanced_acc} full={panel.full_model.metrics.balanced_acc} />
            <Metric label="AUROC (macro)" value={panel.metrics.auroc} full={panel.full_model.metrics.auroc} />
            <Metric label="C-index (PFS)" value={panel.metrics.c_index} full={panel.full_model.metrics.c_index}
              highlight={panel.goal === "survival"} />
          </div>
          <RetainedBar panel={panel} />
          {panel.note && <p className="rounded-md border-l-4 border-coral bg-coral/10 p-2 text-sm">{panel.note}</p>}
          {costPerMarker != null && costPerMarker > 0 && (
            <p className="text-sm">
              Cost per test at your lab's rate: <strong>{(costPerMarker * panel.k).toFixed(2)}</strong>{" "}
              ({panel.k} × {costPerMarker.toFixed(2)})
            </p>
          )}
          <details className="text-xs text-ink/70">
            <summary className="cursor-pointer font-medium text-ink">How these numbers were made</summary>
            <p className="mt-1">{panel.method}. Subtype metrics use the {panel.test_labelled} test patients with a PAM50 call.</p>
            <p className="mt-1">{panel.c_index_note}. {panel.test_events} progression events in the test set.</p>
          </details>
          <Disclaimer compact />
        </div>
      )}
    </Card>
  );
}

function Metric({ label, value, full, highlight }: { label: string; value: number | null; full: number | null; highlight?: boolean }) {
  return (
    <div className={`rounded-md border-2 p-3 ${highlight ? "border-navy bg-sky/60" : "border-ink/15"}`}>
      <div className="text-xs text-ink/70">{label}</div>
      <div className="text-3xl font-bold tabular-nums text-navy">{fmt(value)}</div>
      <div className="text-xs text-ink/70">all 198: {fmt(full)}</div>
    </div>
  );
}

function RetainedBar({ panel }: { panel: Panel }) {
  const pct = (panel.metrics.macro_f1 / panel.full_model.metrics.macro_f1) * 100;
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span>{panel.k} of {panel.full_model.k} proteins retain</span>
        <strong>{pct.toFixed(0)}% of full-model macro-F1</strong>
      </div>
      <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full border border-ink bg-white"
        role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(Math.min(pct, 100))}
        aria-label="Share of full-model macro-F1 retained">
        <div className="h-full bg-navy" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}
