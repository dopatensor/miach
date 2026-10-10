import { useEffect, useMemo, useState } from "react";
import type { Goal, Panel } from "../api";
import { api } from "../api";
import { useAsync } from "../useAsync";
import { QcCard } from "../components/QcCard";
import { LatentMap } from "../components/LatentMap";
import { MarkerList } from "../components/MarkerList";
import { PanelCard } from "../components/PanelCard";
import { Disclaimer } from "../components/Disclaimer";

const K_MAX = 30;

export function Designer() {
  const [disease, setDisease] = useState("brca");
  const [goal, setGoal] = useState<Goal>("subtype");
  const [assay, setAssay] = useState<"IHC" | "qPCR">("IHC");
  const [k, setK] = useState(8);
  const [cost, setCost] = useState("");
  const [panels, setPanels] = useState<Record<number, Panel>>({});
  const [panelError, setPanelError] = useState<string | null>(null);

  const diseases = useAsync(() => api.diseases());
  const qc = useAsync(() => api.qc(disease), [disease]);
  const markers = useAsync(() => api.markers(disease), [disease]);
  const latent = useAsync(() => api.latent(disease), [disease]);

  // Precomputed panels for every k: fetch them all once so the slider is instant.
  useEffect(() => {
    let live = true;
    setPanels({});
    setPanelError(null);
    Promise.all(Array.from({ length: K_MAX }, (_, i) => api.panel(i + 1, goal, disease)))
      .then((ps) => live && setPanels(Object.fromEntries(ps.map((p) => [p.k, p]))))
      .catch((e) => live && setPanelError(String(e)));
    return () => { live = false; };
  }, [goal, disease]);

  const panel = panels[k] ?? null;
  const costNum = useMemo(() => {
    const v = parseFloat(cost);
    return Number.isFinite(v) && v >= 0 ? v : null;
  }, [cost]);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="grid gap-8 lg:grid-cols-[280px_1fr] print:block">
      <aside className="no-print lg:sticky lg:top-6 lg:self-start" aria-label="Panel settings">
        <div className="card space-y-5" style={{ ["--shadow" as string]: "#2E3F8F" }}>
          <h1 className="text-xl font-bold">Design a panel</h1>

          <div>
            <label htmlFor="disease" className="label">Disease</label>
            <select id="disease" value={disease} onChange={(e) => setDisease(e.target.value)}
              className="mt-1 w-full rounded-md border-2 border-ink bg-white px-2 py-1.5">
              {(diseases.data ?? [{ id: "brca", name: "Breast cancer", enabled: true }]).map((d) => (
                <option key={d.id} value={d.id} disabled={!d.enabled}>
                  {d.name}{d.enabled ? "" : " (coming soon)"}
                </option>
              ))}
            </select>
          </div>

          <fieldset>
            <legend className="label">Goal</legend>
            <div className="mt-1 grid grid-cols-2 gap-2">
              {(["subtype", "survival"] as const).map((g) => (
                <label key={g} className={`cursor-pointer rounded-md border-2 border-ink px-2 py-1.5 text-center text-sm font-medium has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-navy ${goal === g ? "bg-navy text-white" : "bg-white"}`}>
                  <input type="radio" name="goal" value={g} checked={goal === g} onChange={() => setGoal(g)} className="sr-only" />
                  {g === "subtype" ? "Subtype" : "Survival"}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="label">Assay type</legend>
            <div className="mt-1 grid grid-cols-2 gap-2">
              {(["IHC", "qPCR"] as const).map((a) => (
                <label key={a} className={`cursor-pointer rounded-md border-2 border-ink px-2 py-1.5 text-center text-sm font-medium has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-navy ${assay === a ? "bg-navy text-white" : "bg-white"}`}>
                  <input type="radio" name="assay" value={a} checked={assay === a} onChange={() => setAssay(a)} className="sr-only" />
                  {a}
                </label>
              ))}
            </div>
            <p className="mt-1 text-xs text-ink/70">Informational for now; markers are ranked from protein data.</p>
          </fieldset>

          <div>
            <div className="flex items-baseline justify-between">
              <label htmlFor="budget" className="label">Marker budget</label>
              <output htmlFor="budget" className="text-2xl font-bold text-navy tabular-nums">{k}</output>
            </div>
            <input id="budget" type="range" min={1} max={K_MAX} step={1} value={k}
              onChange={(e) => setK(Number(e.target.value))}
              aria-valuetext={`${k} markers`}
              className="mt-2 w-full accent-[#2E3F8F]" />
            <div className="flex justify-between text-xs text-ink/70"><span>1</span><span>{K_MAX}</span></div>
          </div>

          <div>
            <label htmlFor="cost" className="label">Cost per marker (optional)</label>
            <input id="cost" type="number" min={0} step="0.01" inputMode="decimal" value={cost}
              onChange={(e) => setCost(e.target.value)} placeholder="your lab's price"
              className="mt-1 w-full rounded-md border-2 border-ink px-2 py-1.5" />
            <p className="mt-1 text-xs text-ink/70">We never estimate prices; enter your own.</p>
          </div>

          <button type="button" className="btn-primary w-full justify-center" onClick={() => window.print()}
            disabled={!panel}>
            Export report
          </button>
        </div>
      </aside>

      <div className="min-w-0 space-y-8">
        <div className="print-only">
          <h1 className="text-2xl font-bold">Miach candidate panel report</h1>
          <p className="text-sm">
            {today} · Breast cancer (TCGA BRCA, RPPA) · goal: {goal} · assay: {assay} · {k} markers
          </p>
          <Disclaimer />
        </div>
        <PanelCard panel={panel} error={panelError} costPerMarker={costNum} />
        <MarkerList markers={markers.data?.markers ?? null} k={k} note={markers.data?.note} error={markers.error} />
        <QcCard qc={qc.data} error={qc.error} />
        <div className="no-print"><LatentMap latent={latent.data} error={latent.error} /></div>
        <div className="print-only text-xs">
          <h2 className="font-bold">Method</h2>
          <p>{markers.data?.method}.</p>
          <p>{panel?.method}.</p>
        </div>
      </div>
    </div>
  );
}
