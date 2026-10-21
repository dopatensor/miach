import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { PatientDetail as Detail } from "../api";
import { SUBTYPES, api, fmt } from "../api";
import { useAsync } from "../useAsync";
import { useAppState } from "../state";
import { Dot, ErrorNote, Section, Skeleton } from "../components/Card";
import { Disclaimer } from "../components/Disclaimer";
import { Ticks } from "./Designer";

export function Patients() {
  const { k, setK } = useAppState();
  const [params, setParams] = useSearchParams();
  const selected = params.get("id");
  const [query, setQuery] = useState("");
  const [subtype, setSubtype] = useState("all");
  const [mismatchOnly, setMismatchOnly] = useState(false);

  const list = useAsync(() => api.patients(k), [k]);
  const detail = useAsync(() => (selected ? api.patient(selected, k) : Promise.resolve(null)), [selected, k]);

  const rows = useMemo(() => (list.data?.patients ?? []).filter((p) =>
    (!query || p.id.toLowerCase().includes(query.toLowerCase())) &&
    (subtype === "all" || p.subtype === subtype) &&
    (!mismatchOnly || p.mismatch)), [list.data, query, subtype, mismatchOnly]);
  const nMismatch = list.data?.patients.filter((p) => p.mismatch).length ?? 0;
  const select = (id: string) => setParams({ id }, { replace: true });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold">patients · locked test set</h1>
          <p className="text-mute">176 TCGA breast tumours the panel never saw. predictions from the top-{k} panel.</p>
        </div>
        <div className="min-w-[200px]">
          <div className="flex items-baseline justify-between">
            <label htmlFor="pbudget" className="label">marker budget</label>
            <output htmlFor="pbudget" className="font-bold tabular-nums">{k}</output>
          </div>
          <input id="pbudget" type="range" min={1} max={30} value={k} onChange={(e) => setK(Number(e.target.value))}
            className="mt-1 w-full accent-[var(--acc)]" aria-valuetext={`${k} markers`} />
          <Ticks k={k} max={30} />
        </div>
      </header>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <Section index={1} title={`${rows.length} of ${list.data?.patients.length ?? 176} patients`} id="plist"
          aside={`${nMismatch} differ from pam50`} className="order-2 lg:order-1">
          <div className="mb-4 flex flex-wrap gap-3">
            <label className="sr-only" htmlFor="q">Search TCGA id</label>
            <input id="q" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search tcga id"
              className="min-w-[180px] flex-1 border border-line bg-bg px-2 py-1" />
            <label className="sr-only" htmlFor="st">PAM50 subtype</label>
            <select id="st" value={subtype} onChange={(e) => setSubtype(e.target.value)} className="border border-line bg-bg px-2 py-1">
              <option value="all">all subtypes</option>
              {SUBTYPES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <label className="flex items-center gap-2 text-mute">
              <input type="checkbox" checked={mismatchOnly} onChange={(e) => setMismatchOnly(e.target.checked)} className="accent-[var(--acc)]" />
              mismatches only
            </label>
          </div>
          {list.error ? <ErrorNote error={list.error} /> : !list.data ? <Skeleton h="h-96" /> : (
            <div className="relative max-h-[70vh] overflow-auto">
              <table className="w-full whitespace-nowrap tabular-nums">
                <caption className="sr-only">Locked test patients with PAM50 subtype and panel prediction</caption>
                <thead className="sticky top-0 bg-bg">
                  <tr className="text-left text-[11px] text-mute">
                    <th scope="col" className="pb-2 pr-3 font-normal">patient</th>
                    <th scope="col" className="pb-2 font-normal">pam50</th>
                    <th scope="col" className="pb-2 font-normal">panel call</th>
                    <th scope="col" className="pb-2 text-right font-normal">conf.</th>
                    <th scope="col" className="pb-2 text-right font-normal">pfs mo</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => (
                    <tr key={p.id} onClick={() => select(p.id)}
                      className={`cursor-pointer border-t border-line ${p.id === selected ? "bg-raise" : "hover:bg-raise"}`}>
                      <td className="py-1.5">
                        <button type="button" onClick={(e) => { e.stopPropagation(); select(p.id); }}
                          aria-current={p.id === selected ? "true" : undefined}
                          className={p.id === selected ? "underline decoration-acc decoration-2 underline-offset-4" : ""}>
                          {p.id}
                        </button>
                      </td>
                      <td>{p.subtype ? <><Dot subtype={p.subtype} />{p.subtype}</> : <span className="text-mute">—</span>}</td>
                      <td><Dot subtype={p.predicted} />{p.predicted}{p.mismatch && <><span aria-hidden="true" className="ml-2 text-acc">≠</span><span className="sr-only"> (differs from PAM50)</span></>}</td>
                      <td className="text-right">{p.confidence.toFixed(2)}</td>
                      <td className="text-right">{p.pfs_months ?? "—"}{p.pfs_event === 1 ? <span title="progression event"> ●</span> : <span className="invisible"> ●</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-3 text-[11px] text-mute">● progression event · <span className="text-acc">≠</span> panel call differs from pam50 (rna)</p>
        </Section>

        <div className="order-1 lg:order-2 lg:sticky lg:top-6 lg:self-start">
          {!selected ? (
            <Section index={2} title="patient"><p className="text-mute">select a patient from the list or click a ring on the patient map.</p></Section>
          ) : detail.error ? <Section title={selected}><ErrorNote error={detail.error} /></Section>
            : !detail.data ? <Section title={selected}><Skeleton h="h-80" /></Section>
            : <PatientCard d={detail.data} />}
        </div>
      </div>
    </div>
  );
}

function PatientCard({ d }: { d: Detail }) {
  const missing = d.markers.filter((m) => m.missing).length;
  return (
    <Section index={2} title={d.id} id="pdetail" aside="test">
      <dl className="grid grid-cols-2 gap-y-3">
        <div><dt className="label">pam50 (rna)</dt><dd className="text-lg">{d.subtype ? <><Dot subtype={d.subtype} />{d.subtype}</> : "—"}</dd></div>
        <div><dt className="label">panel call</dt><dd className="text-lg"><Dot subtype={d.predicted} />{d.predicted}{d.mismatch && <span className="ml-2 text-acc" title="differs from PAM50">≠</span>}</dd></div>
        <div><dt className="label">pfs</dt><dd className="tabular-nums">{d.pfs_months != null ? `${d.pfs_months} mo` : "—"} <span className="text-mute">{d.pfs_event === 1 ? "progressed" : d.pfs_event === 0 ? "censored" : ""}</span></dd></div>
        <div><dt className="label">missing markers</dt><dd className="tabular-nums">{missing} / {d.k}</dd></div>
      </dl>

      <h3 className="label mb-2 mt-6">subtype probabilities</h3>
      <ul className="space-y-1.5">
        {SUBTYPES.map((s) => (
          <li key={s} className="grid grid-cols-[56px_1fr_40px] items-center gap-3">
            <span>{s}</span>
            <span className="relative h-px bg-line">
              <span className="absolute -top-px h-[3px]" style={{ width: `${d.probabilities[s] * 100}%`, background: `var(--c-${s})` }} />
            </span>
            <span className="text-right tabular-nums">{fmt(d.probabilities[s])}</span>
          </li>
        ))}
      </ul>

      <h3 className="label mb-2 mt-6">panel markers vs cohort <span className="normal-case tracking-normal">(z, band = ±1 sd)</span></h3>
      <ul className="space-y-1">
        {d.markers.map((m) => {
          const z = Math.max(-3, Math.min(3, m.z));
          return (
            <li key={m.protein} className="grid grid-cols-[96px_1fr_44px] items-center gap-3">
              <span className="truncate" title={m.protein}>{m.protein}</span>
              <span className="relative h-4" aria-hidden="true">
                <span className="absolute top-1/2 h-px w-full bg-line" />
                <span className="absolute top-1/2 h-1.5 -translate-y-1/2 bg-line" style={{ left: "33.33%", width: "33.33%" }} />
                <span className="absolute top-0.5 h-3 w-px bg-mute" style={{ left: "50%" }} />
                <span className={`absolute top-1/2 h-2 w-2 -translate-x-1 -translate-y-1/2 ${m.missing ? "border border-mute" : "bg-acc"}`}
                  style={{ left: `${((z + 3) / 6) * 100}%` }} />
              </span>
              <span className="text-right tabular-nums">{m.missing ? "imp." : `${m.z > 0 ? "+" : ""}${m.z.toFixed(1)}`}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-[11px] text-mute">imp. = not measured for this patient; imputed with the training median.</p>
      <div className="mt-5 border-t border-line pt-3"><Disclaimer compact /></div>
    </Section>
  );
}
