import { Link } from "react-router-dom";
import { useAsync } from "../useAsync";
import { api } from "../api";
import { ProteinGrid } from "../components/ProteinGrid";

export function Landing() {
  const panel = useAsync(() => api.panel(8));
  const qc = useAsync(() => api.qc());
  const markers = useAsync(() => api.markers());
  const n = (v: number | undefined) => (v == null ? "…" : String(v));
  return (
    <div className="space-y-12 py-2 sm:py-6">
      <section className="hero-glow section grid items-center gap-10 lg:grid-cols-[1fr_440px] lg:p-12">
        <div className="space-y-6">
          <p className="label">research use only · candidate biomarker panels</p>
          <h1 className="text-3xl font-bold leading-tight sm:text-5xl">
            from hundreds of proteins to a few markers a lab can measure.
          </h1>
          <p className="max-w-xl text-lg text-mute">
            pick a disease, a goal and a marker budget. miach returns a small candidate biomarker panel with its held-out
            performance and the evidence behind every marker.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link to="/designer" className="btn-acc">design a panel →</Link>
            <Link to="/evidence" className="btn">evidence</Link>
          </div>
        </div>
        {markers.data ? <ProteinGrid markers={markers.data.markers} k={8} />
          : <div className="skeleton aspect-[22/9]" aria-hidden="true" />}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
      <section aria-labelledby="example" className="section">
        <h2 id="example" className="label">example · breast cancer subtype · 8 markers</h2>
        {panel.data ? (
          <div className="mt-3 space-y-2">
            <p><span className="text-6xl font-bold tracking-tight text-acc tabular-nums font-sans">{panel.data.metrics.macro_f1.toFixed(2)}</span>
              <span className="ml-3 text-mute">macro-f1 vs {panel.data.full_model.metrics.macro_f1.toFixed(2)} with all 198 proteins</span></p>
            <ul className="flex flex-wrap gap-1.5" aria-label="Example panel markers">{panel.data.markers.map((m) => <li key={m} className="chip font-mono">{m}</li>)}</ul>
            <p className="text-xs text-mute">locked test · n = {panel.data.test_n} · preliminary</p>
          </div>
        ) : <div className="skeleton mt-3 h-24" aria-hidden="true" />}
      </section>

      <section aria-labelledby="problem" className="section">
        <h2 id="problem" className="label">the problem in three numbers</h2>
        <dl className="mt-4 grid gap-6 sm:grid-cols-3">
          {([
            [n(qc.data?.n_proteins), "proteins per tumour on TCGA's RPPA platform; no routine assay measures that many."],
            [n(qc.data?.n_patients), "breast tumours with protein data: small, which is why a simple model wins."],
            [n(qc.data?.splits.test.pfs_events), "progression events in the locked test set; survival estimates are underpowered."],
          ] as const).map(([v, t]) => (
            <div key={t}><dt className="text-4xl font-bold tracking-tight tabular-nums font-sans">{v}</dt><dd className="mt-1 text-mute">{t}</dd></div>
          ))}
        </dl>
      </section>
      </div>
    </div>
  );
}
