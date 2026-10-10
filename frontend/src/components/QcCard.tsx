import type { Qc } from "../api";
import { SUBTYPES } from "../api";
import { Card, ErrorNote, Skeleton } from "./Card";

export function QcCard({ qc, error }: { qc: Qc | null; error?: string | null }) {
  return (
    <Card title="Data QC" id="qc-title" shadow="#D4E2FF"
      aside={<span className="text-xs text-ink/70">TCGA BRCA · RPPA protein</span>}>
      {error ? <ErrorNote error={error} /> : !qc ? <Skeleton h="h-28" /> : (
        <div className="space-y-4">
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Patients" value={qc.n_patients} />
            <Stat label="Proteins" value={qc.n_proteins} />
            <Stat label="Missing values" value={`${(qc.missingness.overall * 100).toFixed(1)}%`} />
            <Stat label="Test PFS events" value={qc.splits.test.pfs_events} />
          </dl>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Patients per split and PAM50 subtype</caption>
              <thead>
                <tr className="text-left text-xs text-ink/70">
                  <th scope="col" className="py-1 pr-3">Split</th>
                  <th scope="col" className="pr-3">Patients</th>
                  {SUBTYPES.map((s) => <th scope="col" key={s} className="pr-3">{s}</th>)}
                  <th scope="col" className="pr-3">No PAM50</th>
                  <th scope="col">Events</th>
                </tr>
              </thead>
              <tbody>
                {(["train", "val", "test"] as const).map((k) => {
                  const s = qc.splits[k];
                  return (
                    <tr key={k} className={`border-t border-ink/10 ${k === "test" ? "font-semibold" : ""}`}>
                      <th scope="row" className="py-1 pr-3 text-left">{k === "test" ? "test (locked)" : k}</th>
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
          <p className="text-xs text-ink/70">
            {qc.missingness.proteins_any_missing} proteins have some missing values
            ({qc.missingness.proteins_fully_missing} are not measured in this cohort). Imputation: {qc.imputation}.
          </p>
        </div>
      )}
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md bg-sky/50 p-2">
      <dt className="text-xs text-ink/70">{label}</dt>
      <dd className="text-xl font-bold text-navy">{value}</dd>
    </div>
  );
}
