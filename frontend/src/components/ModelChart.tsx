import type { Models } from "../api";
import { ErrorNote, Section, Skeleton, TestSetTag } from "./Card";

const MAX = 0.8;
const pos = (v: number) => `${(v / MAX) * 100}%`;

/** Dot plot: one row per model, hollow mark = 10% labels, filled mark = 100% labels. */
export function ModelChart({ models, error }: { models: Models | null; error?: string | null }) {
  return (
    <Section index={1} title="six-model comparison · subtype macro-f1" id="models-title" aside={<TestSetTag />}>
      {error ? <ErrorNote error={error} /> : !models ? <Skeleton h="h-64" /> : (
        <>
          <p className="mb-4 flex gap-6 text-xs text-mute">
            <span><span aria-hidden="true" className="mr-1.5 inline-block h-2 w-2 border border-fg align-middle" />10% labels</span>
            <span><span aria-hidden="true" className="mr-1.5 inline-block h-2 w-2 bg-fg align-middle" />100% labels</span>
          </p>
          <table className="w-full">
            <caption className="sr-only">Subtype macro-F1 per model with 10% and 100% of training labels</caption>
            <thead>
              <tr className="text-left text-xs text-mute">
                <th scope="col" className="pb-2 font-normal">model</th>
                <th scope="col" className="hidden w-1/2 pb-2 font-normal md:table-cell">
                  <div className="flex justify-between"><span>0</span><span>0.4</span><span>0.8</span></div>
                </th>
                <th scope="col" className="pb-2 text-right font-normal">10%</th>
                <th scope="col" className="pb-2 text-right font-normal">100%</th>
              </tr>
            </thead>
            <tbody>
              {models.models.map((m) => (
                <tr key={m.model} className="border-t border-line">
                  <td className="py-2 pr-3">
                    {m.model.toLowerCase()}
                    <span className="text-mute">{m.production ? " · production" : m.kind === "deep" ? " · research" : ""}</span>
                  </td>
                  <td className="hidden md:table-cell">
                    <div className="relative h-3">
                      <div className="absolute top-1/2 h-px w-full bg-line" />
                      <div className="absolute top-1/2 h-px bg-mute" style={{ left: pos(Math.min(m.f1_10, m.f1_100)), width: `${(Math.abs(m.f1_100 - m.f1_10) / MAX) * 100}%` }} />
                      <div className="absolute top-0.5 h-2 w-2 -translate-x-1 border border-fg bg-bg" style={{ left: pos(m.f1_10) }} title={`10% labels: ${m.f1_10.toFixed(2)}`} />
                      <div className="absolute top-0.5 h-2 w-2 -translate-x-1 bg-fg" style={{ left: pos(m.f1_100) }} title={`100% labels: ${m.f1_100.toFixed(2)}`} />
                    </div>
                  </td>
                  <td className="text-right tabular-nums">{m.f1_10.toFixed(2)}</td>
                  <td className="text-right tabular-nums">{m.f1_100.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-mute">
            source: {models.source}. this site's rebuild of the elastic net (own split, 100% labels) scores{" "}
            {models.rebuild_check.macro_f1.toFixed(3)} on its locked test set.
          </p>
        </>
      )}
    </Section>
  );
}
