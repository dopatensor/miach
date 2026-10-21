import { api, ENCODER_LABELS, fmt, type Cancer, type ResultRow, type Results as R } from "../api";
import { useAsync } from "../useAsync";
import { ErrorNote, Section, Skeleton } from "../components/Card";
import { Disclaimer } from "../components/Disclaimer";

const OV_NOTE = "Survival only: no public subtype labels";

function row(d: R, encoder: string, cancer: string, fraction: number): ResultRow | undefined {
  return d.rows.find((r) => r.encoder === encoder && r.cancer === cancer && r.fraction === fraction);
}

// Encoder with the highest value of `get` for one cancer (ties: first in file order).
function best(d: R, cancer: string, get: (enc: string) => number | null | undefined): string | null {
  let top: string | null = null, v = -Infinity;
  for (const e of d.encoders) {
    const x = get(e);
    if (x != null && x > v) { v = x; top = e; }
  }
  return top;
}

function Cell({ main, sub, ci, isBest }: { main: string; sub?: string; ci?: string; isBest: boolean }) {
  return (
    <td className={`py-1.5 pr-3 tabular-nums ${isBest ? "font-bold text-fg" : "text-mute"}`}>
      <span className={isBest ? "underline decoration-acc decoration-2 underline-offset-4" : ""}>{main}</span>
      {sub && <span className="font-normal text-mute"> [{sub}]</span>}
      {isBest && <span className="sr-only"> (best for this cancer)</span>}
      {isBest && <span aria-hidden="true" className="ml-1 text-acc">★</span>}
      {ci && <div className="text-[10px] font-normal text-mute">95% CI {ci}</div>}
    </td>
  );
}

function ClassificationTable({ d }: { d: R }) {
  const cls = d.cancers.filter((c) => c.task);
  const surv = d.cancers.filter((c) => !c.task);
  const f1 = (e: string, c: string, f: number) => row(d, e, c, f)?.macro_f1 ?? null;
  const winners = Object.fromEntries(cls.map((c) => [c.id, best(d, c.id, (e) => f1(e, c.id, 1))]));
  return (
    <div className="relative overflow-x-auto">
      <table className="w-full min-w-[560px]">
        <caption className="sr-only">Macro-F1 at 100% training labels, 10% labels in brackets, per cancer</caption>
        <thead>
          <tr className="text-left text-xs text-mute">
            <th scope="col" className="pr-3">model</th>
            {cls.map((c) => <th key={c.id} scope="col" className="pr-3">{c.name.toLowerCase()}</th>)}
            {surv.map((c) => <th key={c.id} scope="col" className="pr-3">{c.name.toLowerCase()}</th>)}
          </tr>
        </thead>
        <tbody>
          {d.encoders.map((e, i) => (
            <tr key={e} className="border-t border-line align-top">
              <th scope="row" className="py-1.5 pr-3 text-left font-normal">{ENCODER_LABELS[e] ?? e}</th>
              {cls.map((c) => {
                const r = row(d, e, c.id, 1);
                return <Cell key={c.id} main={fmt(r?.macro_f1)} sub={fmt(f1(e, c.id, 0.1))}
                  ci={r?.f1_lo != null ? `${fmt(r.f1_lo)}–${fmt(r.f1_hi)}` : undefined} isBest={winners[c.id] === e} />;
              })}
              {surv.map((c) => i === 0 ? (
                <td key={c.id} rowSpan={d.encoders.length} className="max-w-[10rem] pr-3 align-middle text-[11px] text-mute">{OV_NOTE}</td>
              ) : null)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SurvivalTable({ d }: { d: R }) {
  // C-index does not depend on the label fraction; read the 100% row.
  const c = (e: string, id: string) => row(d, e, id, 1);
  const winners = Object.fromEntries(d.cancers.map((k) => [k.id, best(d, k.id, (e) => c(e, k.id)?.c_index)]));
  return (
    <div className="relative overflow-x-auto">
      <table className="w-full min-w-[560px]">
        <caption className="sr-only">Survival C-index per cancer</caption>
        <thead>
          <tr className="text-left text-xs text-mute">
            <th scope="col" className="pr-3">model</th>
            {d.cancers.map((k) => <th key={k.id} scope="col" className="pr-3">{k.name.toLowerCase()} <span className="font-normal">({k.survival})</span></th>)}
          </tr>
        </thead>
        <tbody>
          {d.encoders.map((e) => (
            <tr key={e} className="border-t border-line align-top">
              <th scope="row" className="py-1.5 pr-3 text-left font-normal">{ENCODER_LABELS[e] ?? e}</th>
              {d.cancers.map((k) => {
                const r = c(e, k.id);
                return <Cell key={k.id} main={fmt(r?.c_index)} ci={r ? `${fmt(r.c_lo)}–${fmt(r.c_hi)}` : undefined} isBest={winners[k.id] === e} />;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Tasks({ cancers }: { cancers: Cancer[] }) {
  return (
    <ul className="grid gap-x-6 gap-y-1 text-[11px] text-mute sm:grid-cols-2">
      {cancers.map((c) => (
        <li key={c.id}><span className="text-fg">{c.name.toLowerCase()}</span> · {c.task ?? OV_NOTE.toLowerCase()} · survival: {c.survival}</li>
      ))}
    </ul>
  );
}

export function Results() {
  const { data, error } = useAsync(() => api.results());
  return (
    <div className="space-y-10">
      <header className="max-w-3xl space-y-1">
        <h1 className="text-lg font-bold">results · four cancers</h1>
        <p className="text-mute">
          Five encoders, four TCGA cancers, protein (RPPA) data only. Every number is measured once on each
          cancer's locked test set and is <strong className="text-fg">preliminary</strong>. ★ marks the best model per cancer.
        </p>
      </header>
      {error ? <ErrorNote error={error} /> : !data ? <><Skeleton h="h-48" /><Skeleton h="h-48" /></> : (
        <>
          <Section index={1} title="classification · macro-F1" id="cls-title" aside="locked test set · preliminary">
            <p className="mb-3 text-mute">100% of training labels, 10% in [brackets]. Higher is better.</p>
            <ClassificationTable d={data} />
          </Section>
          <Section index={2} title="survival · C-index" id="surv-title" aside="locked test set · preliminary">
            <p className="mb-3 text-mute">0.50 = random ordering of patients by risk. Wide intervals mean few events: read these as weak evidence.</p>
            <SurvivalTable d={data} />
          </Section>
          <Section index={3} title="tasks" id="tasks-title">
            <Tasks cancers={data.cancers} />
            <p className="mt-3 text-[11px] text-mute">source: {data.source}</p>
          </Section>
          <Disclaimer compact />
        </>
      )}
    </div>
  );
}
