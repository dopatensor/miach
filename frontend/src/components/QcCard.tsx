import type { Qc } from "../api";
import { SUBTYPES } from "../api";
import { ErrorNote, Skeleton } from "./Card";

export function QcCard({ qc, error }: { qc: Qc | null; error?: string | null }) {
  if (error) return <ErrorNote error={error} />;
  if (!qc) return <Skeleton h="h-28" />;
  return (
    <div className="space-y-4">
      <dl className="flex flex-wrap gap-x-10 gap-y-2">
        {([["patients", qc.n_patients], ["proteins", qc.n_proteins],
          ["missing values", `${(qc.missingness.overall * 100).toFixed(1)}%`], ["test pfs events", qc.splits.test.pfs_events]] as const)
          .map(([l, v]) => <div key={l}><dt className="label">{l}</dt><dd className="text-xl tabular-nums">{v}</dd></div>)}
      </dl>
      <div className="overflow-x-auto">
        <table className="w-full tabular-nums">
          <caption className="sr-only">Patients per split and PAM50 subtype</caption>
          <thead>
            <tr className="text-left text-[11px] text-mute">
              <th scope="col" className="pb-2 pr-3 font-normal">split</th>
              <th scope="col" className="pr-3 font-normal">n</th>
              {SUBTYPES.map((s) => <th scope="col" key={s} className="pr-3 font-normal">{s}</th>)}
              <th scope="col" className="pr-3 font-normal">no pam50</th>
              <th scope="col" className="font-normal">events</th>
            </tr>
          </thead>
          <tbody>
            {(["train", "val", "test"] as const).map((k) => {
              const s = qc.splits[k];
              return (
                <tr key={k} className="border-t border-line">
                  <th scope="row" className="py-1.5 pr-3 text-left font-normal">{k === "test" ? "test (locked)" : k}</th>
                  <td className="pr-3">{s.patients}</td>
                  {SUBTYPES.map((c) => <td key={c} className="pr-3">{s.subtypes[c]}</td>)}
                  <td className="pr-3">{s.unlabelled}</td>
                  <td>{s.pfs_events}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-mute">
        {qc.missingness.proteins_any_missing} proteins have missing values ({qc.missingness.proteins_fully_missing} not
        measured in this cohort). imputation: {qc.imputation}.
      </p>
    </div>
  );
}
