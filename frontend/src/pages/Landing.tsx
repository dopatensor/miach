import { Link } from "react-router-dom";
import { useAsync } from "../useAsync";
import { api } from "../api";

export function Landing() {
  const panel = useAsync(() => api.panel(8));
  const qc = useAsync(() => api.qc());
  const n = (v: number | undefined) => (v == null ? "…" : String(v));
  return (
    <div className="max-w-3xl space-y-14 py-6">
      <section className="space-y-6">
        <h1 className="text-2xl font-bold leading-snug sm:text-3xl">
          from hundreds of proteins to a few markers a lab can measure.
        </h1>
        <p className="text-mute">
          pick a disease, a goal and a marker budget. miach returns a small candidate biomarker panel with its held-out
          performance and the evidence behind every marker.
        </p>
        <div className="flex flex-wrap gap-4">
          <Link to="/designer" className="btn-acc">design a panel →</Link>
          <Link to="/evidence" className="btn">evidence</Link>
        </div>
      </section>

      <section aria-labelledby="example" className="border-t border-line pt-6">
        <h2 id="example" className="label">example · breast cancer subtype · 8 markers</h2>
        {panel.data ? (
          <div className="mt-3 space-y-2">
            <p><span className="text-5xl font-bold tabular-nums">{panel.data.metrics.macro_f1.toFixed(2)}</span>
              <span className="ml-3 text-mute">macro-f1 vs {panel.data.full_model.metrics.macro_f1.toFixed(2)} with all 198 proteins</span></p>
            <p className="text-mute">{panel.data.markers.join(" · ")}</p>
            <p className="text-[11px] text-mute">locked test · n = {panel.data.test_n} · preliminary</p>
          </div>
        ) : <div className="skeleton mt-3 h-24" aria-hidden="true" />}
      </section>

      <section aria-labelledby="problem" className="border-t border-line pt-6">
        <h2 id="problem" className="label">the problem in three numbers</h2>
        <dl className="mt-4 grid gap-6 sm:grid-cols-3">
          {([
            [n(qc.data?.n_proteins), "proteins per tumour on TCGA's RPPA platform; no routine assay measures that many."],
            [n(qc.data?.n_patients), "breast tumours with protein data: small, which is why a simple model wins."],
            [n(qc.data?.splits.test.pfs_events), "progression events in the locked test set; survival estimates are underpowered."],
          ] as const).map(([v, t]) => (
            <div key={t}><dt className="text-3xl font-bold tabular-nums">{v}</dt><dd className="mt-1 text-mute">{t}</dd></div>
          ))}
        </dl>
      </section>
    </div>
  );
}
