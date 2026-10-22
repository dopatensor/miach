import { useEffect, useMemo, useState } from "react";
import type { Goal, Panel } from "../api";
import { api, PANEL_CANCERS } from "../api";
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
  const live = PANEL_CANCERS.includes(cancer);
  const results = useAsync(() => api.results());
  // Lung / colorectal ranking comes from the four-cancer run (markers_<cancer>.csv); breast keeps its own build.
  const multiMarkers = useAsync(() => (cancer === "brca" || !live ? Promise.resolve(null) : api.cancerMarkers(cancer)), [cancer]);
  const cancerName = results.data?.cancers.find((c) => c.id === cancer)?.name.toLowerCase() ?? cancer;
  const qc = useAsync(() => api.qc());
  const markers = useAsync(() => api.markers());
  const latent = useAsync(() => api.latent());

  // Precomputed panels for every k, fetched once so the slider is instant.
  useEffect(() => {
    let active = true;
    setPanels({});
    setPanelError(null);
    if (!PANEL_CANCERS.includes(cancer)) return;
    Promise.all(Array.from({ length: K_MAX }, (_, i) => api.panel(i + 1, goal, cancer)))
      .then((ps) => active && setPanels(Object.fromEntries(ps.map((p) => [p.k, p]))))
      .catch((e) => active && setPanelError(String(e)));
    return () => { active = false; };
  }, [goal, cancer]);

  const panel = panels[k] ?? null;
  const costNum = useMemo(() => {
    const v = parseFloat(cost);
    return Number.isFinite(v) && v >= 0 ? v : null;
  }, [cost]);

  return (
    <div className="space-y-6">
      <div className="no-print section flex flex-wrap items-end gap-x-10 gap-y-5" role="group" aria-label="Panel settings">
        <h1 className="sr-only">Design a panel</h1>
        <div>
          <label htmlFor="disease" className="label block">disease</label>
          <select id="disease" value={cancer} onChange={(e) => setCancer(e.target.value)} className="mt-2">
            {(results.data?.cancers ?? [{ id: "brca", name: "Breast" }]).map((c) => (
              <option key={c.id} value={c.id}>{c.name.toLowerCase()}{PANEL_CANCERS.includes(c.id) ? " · live panel" : " · results only"}</option>
            ))}
          </select>
        </div>
        {live && <>
        <Segmented label="goal" value={goal} options={["subtype", "survival"]} onChange={(v) => setGoal(v as Goal)} />
        <div className="min-w-[220px] flex-1">
          <div className="flex items-baseline justify-between">
            <label htmlFor="budget" className="label">marker budget</label>
            <output htmlFor="budget" className="text-2xl font-bold text-acc tabular-nums">{k}</output>
          </div>
          <input id="budget" type="range" min={1} max={K_MAX} step={1} value={k}
            onChange={(e) => setK(Number(e.target.value))} aria-valuetext={`${k} markers`}
            className="mt-2 h-2 w-full cursor-pointer" />
          <Ticks k={k} max={K_MAX} />
        </div>
        <details className="relative">
          <summary className="cursor-pointer rounded-full px-1 text-sm text-mute hover:text-fg">assay &amp; cost</summary>
          <div className="mt-3 space-y-3 sm:absolute sm:right-0 sm:z-10 sm:w-72 sm:rounded-xl sm:border sm:border-line sm:bg-raise sm:p-5 sm:shadow-2xl">
            <Segmented label="assay" value={assay} options={["IHC", "qPCR"]} onChange={(v) => setAssay(v as "IHC" | "qPCR")} />
            <p className="text-xs text-mute">informational; markers are ranked from protein data.</p>
            <div>
              <label htmlFor="cost" className="label block">cost per marker</label>
              <input id="cost" type="number" min={0} step="0.01" inputMode="decimal" value={cost}
                onChange={(e) => setCost(e.target.value)} placeholder="your lab's price"
                className="mt-2 w-full" />
              <p className="mt-1 text-xs text-mute">never estimated; enter your own.</p>
            </div>
          </div>
        </details>
        <button type="button" className="btn-acc" onClick={() => window.print()} disabled={!panel}>export</button>
        </>}
      </div>

      {!live ? <CancerResults cancer={cancer} results={results.data} /> : <>

      <div className="print-only">
        <h1 className="text-2xl font-bold sm:text-3xl">miach · candidate panel report</h1>
        <p>{new Date().toISOString().slice(0, 10)} · {cancer === "brca" ? "breast cancer (TCGA BRCA, RPPA)" : `${cancerName} cancer (TCGA, RPPA; four-cancer split)`} · goal {goal} · assay {assay} · {k} markers</p>
        <Disclaimer />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr] print:block print:space-y-4">
        <PanelCard panel={panel} error={panelError} costPerMarker={costNum} onPickK={setK}
          curve={Object.values(panels).sort((a, b) => a.k - b.k).map((p) => ({ k: p.k, f1: p.metrics.macro_f1 }))} />
        {cancer === "brca"
          ? <MarkerList markers={markers.data?.markers ?? null} k={k} note={markers.data?.note} error={markers.error} />
          : <MarkerList markers={multiMarkers.data?.markers ?? null} k={k} error={multiMarkers.error}
              footnote={multiMarkers.data ? `${multiMarkers.data.method}.` : undefined} />}
      </div>

      {cancer !== "brca" ? <div className="no-print"><CancerResults cancer={cancer} results={results.data} panelLive /></div> : <>
      <section className="section no-print" aria-label="Cohort">
        <div role="tablist" aria-label="Cohort views" className="mb-5 flex flex-wrap items-center gap-2">
          <span aria-hidden="true" className="label mr-2 inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-accsoft px-1.5 text-[11px] text-acc">03</span>
          {TABS.map((t) => (
            <button key={t} role="tab" type="button" aria-selected={tab === t} aria-controls={`tab-${t}`} id={`tabbtn-${t}`}
              onClick={() => setTab(t)}
              className={`label rounded-full px-3 py-1.5 transition-colors ${tab === t ? "bg-raise-2 text-fg" : "hover:text-fg"}`}>
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
        <p className="text-xs">method: {markers.data?.method}. {panel?.method}.</p>
      </div>
      </>}
      {cancer !== "brca" && (
        <p className="print-only text-xs">method: {multiMarkers.data?.method}. {panel?.method}.</p>
      )}
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
      <div className="mt-2 inline-flex rounded-full border border-line bg-raise-2 p-0.5">
        {options.map((o) => (
          <label key={o} className={`cursor-pointer rounded-full px-3.5 py-1 text-sm transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-1 has-[:focus-visible]:outline-acc ${value === o ? "bg-fg text-bg" : "text-mute hover:text-fg"}`}>
            <input type="radio" name={label} value={o} checked={value === o} onChange={() => onChange(o)} className="sr-only" />
            {o.toLowerCase()}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
