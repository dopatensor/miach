import { Link } from "react-router-dom";
import { useAsync } from "../useAsync";
import { api } from "../api";
import { Disclaimer } from "../components/Disclaimer";

export function Landing() {
  const panel = useAsync(() => api.panel(8));
  const qc = useAsync(() => api.qc());
  return (
    <div className="space-y-16">
      <section className="grid items-center gap-10 py-6 md:grid-cols-[1.3fr_1fr]">
        <div className="space-y-6">
          <p className="label">Biomarker panel designer</p>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            From hundreds of proteins to a <span className="bg-sun px-1">few markers</span> a lab can actually measure.
          </h1>
          <p className="max-w-xl text-lg text-ink/80">
            Pick a disease, a goal and a marker budget. Miach returns a small, assay-ready candidate panel with its
            held-out performance and the evidence behind every marker.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/designer" className="btn-primary">Design a panel →</Link>
            <Link to="/evidence" className="btn-secondary">See the evidence</Link>
          </div>
        </div>
        <div className="card" style={{ ["--shadow" as string]: "#E47A59" }}>
          <p className="label">Example · breast cancer subtype · 8 markers</p>
          {panel.data ? (
            <>
              <p className="mt-3 text-5xl font-bold text-navy tabular-nums">{panel.data.metrics.macro_f1.toFixed(2)}</p>
              <p className="text-sm">macro-F1 with 8 proteins vs {panel.data.full_model.metrics.macro_f1.toFixed(2)} with all 198</p>
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {panel.data.markers.map((m) => <li key={m} className="chip bg-sky">{m}</li>)}
              </ul>
              <p className="mt-3 text-xs text-ink/70">Locked test set · n = {panel.data.test_n} · preliminary</p>
            </>
          ) : <div className="skeleton mt-3 h-32" aria-hidden="true" />}
        </div>
      </section>

      <section aria-labelledby="problem">
        <h2 id="problem" className="mb-6 text-2xl font-bold">The problem, in three numbers</h2>
        <div className="grid gap-6 md:grid-cols-3">
          <Fact n={qc.data ? String(qc.data.n_proteins) : "…"} text="proteins measured per tumour in TCGA's RPPA platform; no routine assay runs that many." />
          <Fact n={qc.data ? String(qc.data.n_patients) : "…"} text="breast tumours with protein data: small for deep learning, which is why a simple model wins here." />
          <Fact n={qc.data ? String(qc.data.splits.test.pfs_events) : "…"} text="progression events in the locked test set, so survival estimates are honest but underpowered." />
        </div>
      </section>

      <section className="rounded-lg border-2 border-ink bg-sky/40 p-6">
        <Disclaimer />
      </section>
    </div>
  );
}

function Fact({ n, text }: { n: string; text: string }) {
  return (
    <div className="card" style={{ ["--shadow" as string]: "#D4E2FF" }}>
      <p className="text-4xl font-bold text-navy tabular-nums">{n}</p>
      <p className="mt-2 text-sm">{text}</p>
    </div>
  );
}
