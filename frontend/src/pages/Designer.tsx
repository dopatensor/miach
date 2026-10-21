import { useEffect, useMemo, useState } from "react";
import type { Goal, Panel } from "../api";
import { api } from "../api";
import { useAsync } from "../useAsync";
import { useAppState } from "../state";
import { QcCard } from "../components/QcCard";
import { LatentMap } from "../components/LatentMap";
import { MarkerList } from "../components/MarkerList";
import { PanelCard } from "../components/PanelCard";
import { Disclaimer } from "../components/Disclaimer";
import { CancerResults } from "../components/CancerResults";

const K_MAX = 30;
const TABS = ["map", "qc", "method"] as const;

export function Designer() {
  const { k, setK } = useAppState();
  const [goal, setGoal] = useState<Goal>("subtype");
  const [assay, setAssay] = useState<"IHC" | "qPCR">("IHC");
  const [cost, setCost] = useState("");
  const [tab, setTab] = useState<(typeof TABS)[number]>("map");
  const [panels, setPanels] = useState<Record<number, Panel>>({});
  const [panelError, setPanelError] = useState<string | null>(null);

  const [cancer, setCancer] = useState("brca");
  const results = useAsync(() => api.results());
  const qc = useAsync(() => api.qc());
  const markers = useAsync(() => api.markers());
  const latent = useAsync(() => api.latent());

  // Precomputed panels for every k, fetched once so the slider is instant.
  useEffect(() => {
    let live = true;
    setPanels({});
    setPanelError(null);
    Promise.all(Array.from({ length: K_MAX }, (_, i) => api.panel(i + 1, goal)))
      .then((ps) => live && setPanels(Object.fromEntries(ps.map((p) => [p.k, p]))))
      .catch((e) => live && setPanelError(String(e)));
    return () => { live = false; };
  }, [goal]);

  const panel = panels[k] ?? null;
  const costNum = useMemo(() => {
    const v = parseFloat(cost);
    return Number.isFinite(v) && v >= 0 ? v : null;
  }, [cost]);

  return (
    <div className="space-y-6">
      <div className="no-print section flex flex-wrap items-end gap-x-8 gap-y-4" role="group" aria-label="Panel settings">
        <h1 className="sr-only">Design a panel</h1>
        <div>
          <label htmlFor="disease" className="label block">disease</label>
          <select id="disease" value={cancer} onChange={(e) => setCancer(e.target.value)} className="mt-1 border border-line bg-bg px-2 py-1">
            {(results.data?.cancers ?? [{ id: "brca", name: "Breast" }]).map((c) => (
              <option key={c.id} value={c.id}>{c.name.toLowerCase()}{c.id === "brca" ? " · live panel" : " · results only"}</option>
            ))}
          </select>
        </div>
        {cancer === "brca" && <>
        <Segmented label="goal" value={goal} options={["subtype", "survival"]} onChange={(v) => setGoal(v as Goal)} />
        <div className="min-w-[220px] flex-1">
          <div className="flex items-baseline justify-between">
            <label htmlFor="budget" className="label">marker budget</label>
            <output htmlFor="budget" className="text-lg font-bold tabular-nums">{k}</output>
          </div>
          <input id="budget" type="range" min={1} max={K_MAX} step={1} value={k}
            onChange={(e) => setK(Number(e.target.value))} aria-valuetext={`${k} markers`}
            className="mt-2 w-full accent-[var(--acc)]" />
          <Ticks k={k} max={K_MAX} />
        </div>
        <details className="relative">
          <summary className="cursor-pointer text-mute hover:text-fg">assay &amp; cost</summary>
          <div className="mt-3 space-y-3 sm:absolute sm:right-0 sm:z-10 sm:w-64 sm:border sm:border-line sm:bg-bg sm:p-4">
            <Segmented label="assay" value={assay} options={["IHC", "qPCR"]} onChange={(v) => setAssay(v as "IHC" | "qPCR")} />
            <p className="text-[11px] text-mute">informational; markers are ranked from protein data.</p>
            <div>
              <label htmlFor="cost" className="label block">cost per marker</label>
              <input id="cost" type="number" min={0} step="0.01" inputMode="decimal" value={cost}
                onChange={(e) => setCost(e.target.value)} placeholder="your lab's price"
                className="mt-1 w-full border border-line bg-bg px-2 py-1" />
              <p className="mt-1 text-[11px] text-mute">never estimated; enter your own.</p>
            </div>
          </div>
        </details>
        <button type="button" className="btn-acc" onClick={() => window.print()} disabled={!panel}>export</button>
        </>}
      </div>

      {cancer !== "brca" ? <CancerResults cancer={cancer} results={results.data} /> : <>

      <div className="print-only">
        <h1 className="text-lg font-bold">miach · candidate panel report</h1>
        <p>{new Date().toISOString().slice(0, 10)} · breast cancer (TCGA BRCA, RPPA) · goal {goal} · assay {assay} · {k} markers</p>
        <Disclaimer />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr] print:block print:space-y-4">
        <PanelCard panel={panel} error={panelError} costPerMarker={costNum} onPickK={setK}
          curve={Object.values(panels).sort((a, b) => a.k - b.k).map((p) => ({ k: p.k, f1: p.metrics.macro_f1 }))} />
        <MarkerList markers={markers.data?.markers ?? null} k={k} note={markers.data?.note} error={markers.error} />
      </div>

      <section className="section no-print" aria-label="Cohort">
        <div role="tablist" aria-label="Cohort views" className="mb-4 flex gap-5">
          <span className="label text-fg" aria-hidden="true">03</span>
          {TABS.map((t) => (
            <button key={t} role="tab" type="button" aria-selected={tab === t} aria-controls={`tab-${t}`} id={`tabbtn-${t}`}
              onClick={() => setTab(t)}
              className={tab === t ? "label text-fg underline decoration-acc decoration-2 underline-offset-[6px]" : "label hover:text-fg"}>
              {t === "map" ? "patient map" : t === "qc" ? "data qc" : "method"}
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`tab-${tab}`} aria-labelledby={`tabbtn-${tab}`}>
          {tab === "map" && <LatentMap latent={latent.data} error={latent.error} />}
          {tab === "qc" && <QcCard qc={qc.data} error={qc.error} />}
          {tab === "method" && (
            <div className="max-w-3xl space-y-2 text-mute">
              <p><span className="text-fg">ranking.</span> {markers.data?.method}.</p>
              <p><span className="text-fg">panel model.</span> {panel?.method}.</p>
            </div>
          )}
        </div>
      </section>

      <div className="print-only space-y-2">
        <QcCard qc={qc.data} />
        <p className="text-[11px]">method: {markers.data?.method}. {panel?.method}.</p>
      </div>
      </>}
    </div>
  );
}

/** One hairline tick per budget step; filled up to the current k. */
export function Ticks({ k, max }: { k: number; max: number }) {
  return (
    <div className="mt-1 flex justify-between px-[7px]" aria-hidden="true">
      {Array.from({ length: max }, (_, i) => (
        <span key={i} className="w-px" style={{ height: (i + 1) % 5 === 0 || i === 0 ? 7 : 4, background: i < k ? "var(--fg)" : "var(--line)" }} />
      ))}
    </div>
  );
}

function Segmented({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void;
}) {
  return (
    <fieldset>
      <legend className="label">{label}</legend>
      <div className="mt-1 flex border border-line">
        {options.map((o) => (
          <label key={o} className={`cursor-pointer px-3 py-1 has-[:focus-visible]:outline has-[:focus-visible]:outline-1 has-[:focus-visible]:outline-acc ${value === o ? "bg-fg text-bg" : "text-mute hover:text-fg"}`}>
            <input type="radio" name={label} value={o} checked={value === o} onChange={() => onChange(o)} className="sr-only" />
            {o.toLowerCase()}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
