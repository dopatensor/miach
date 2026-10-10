import { api } from "../api";
import { useAsync } from "../useAsync";
import { Card, ErrorNote, Skeleton } from "../components/Card";
import { ModelChart } from "../components/ModelChart";

const BOTTLENECKS: [string, string, string][] = [
  ["Small data favours simple models", "~600 labelled training tumours; the elastic net beat every deep encoder.", "Elastic net in production; deep models stay a research track."],
  ["Protein-only ceiling", "PAM50 is defined from RNA; 198 proteins cannot fully reproduce an RNA label.", "RNA and multi-omics fusion are in development, not in the live engine."],
  ["Survival underpowered", "Only 23 progression events in the locked test set.", "C-index shown for reference; survival-specific ranking not built yet."],
  ["JEPA shortcut / dimensional collapse", "The pathway JEPA learned a low-rank shortcut and under-performed (0.39 at 10% labels).", "Kept off the product flow."],
  ["Correlated markers share credit", "PR ranks low because ER-alpha carries much of the same signal.", "Stability and the known-driver check are shown with every ranking."],
  ["Pretrained-model leakage & licences", "Foundation models may have seen TCGA, and some licences forbid commercial use.", "No pretrained model in production until checked."],
];

export function Evidence() {
  const markers = useAsync(() => api.markers());
  const models = useAsync(() => api.models());
  const qc = useAsync(() => api.qc());
  return (
    <div className="space-y-10">
      <header className="max-w-3xl space-y-2">
        <h1 className="text-3xl font-bold">Evidence</h1>
        <p>What we measured, what won, and where it falls short. Deep models below are a research track and are not used in the Designer.</p>
      </header>

      <ModelChart models={models.data} error={models.error} />

      <div className="grid gap-8 lg:grid-cols-2">
        <Card title="Known-driver check" id="known-title" shadow="#D4E2FF">
          {markers.error ? <ErrorNote error={markers.error} /> : !markers.data ? <Skeleton /> : (
            <>
              <p className="mb-3 text-sm">Does the ranking rediscover markers biologists already trust? Rank out of {markers.data.markers.length}.</p>
              <table className="w-full text-sm">
                <caption className="sr-only">Rank of known breast cancer markers</caption>
                <thead><tr className="text-left text-xs text-ink/70"><th scope="col">Marker</th><th scope="col">Rank</th><th scope="col">Why it matters</th></tr></thead>
                <tbody>
                  {markers.data.known_markers.map((m) => (
                    <tr key={m.protein} className="border-t border-ink/10 align-top">
                      <td className="py-1.5 pr-2 font-semibold">{m.protein}{m.gene !== m.protein && <span className="font-normal text-ink/60"> {m.gene}</span>}</td>
                      <td className="pr-2 tabular-nums">#{m.rank}</td>
                      <td>{m.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs text-ink/70">{markers.data.note}</p>
            </>
          )}
        </Card>

        <Card title="Validation design" id="validation-title" shadow="#D4E2FF">
          {qc.error ? <ErrorNote error={qc.error} /> : !qc.data ? <Skeleton /> : (
            <ul className="list-disc space-y-2 pl-5 text-sm">
              <li>Patient-level split with a fixed seed: {qc.data.splits.train.patients} train · {qc.data.splits.val.patients} validation · <strong>{qc.data.splits.test.patients} locked test</strong>.</li>
              <li>Hyperparameters (regularisation strength) are chosen on the validation split only.</li>
              <li>Marker ranking uses bootstrap refits on training patients, scored on out-of-bag and validation patients. The test split never influences ranking or model choice.</li>
              <li>Each panel is scored once on the locked test set ({qc.data.splits.test.labelled} patients with a PAM50 call, {qc.data.splits.test.pfs_events} progression events).</li>
              <li>All numbers are <strong>preliminary</strong>: one cohort, one split, no external validation yet.</li>
            </ul>
          )}
        </Card>
      </div>

      <Card title="Known bottlenecks" id="bottlenecks-title" shadow="#E47A59">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Known limitations and how we handle them</caption>
            <thead><tr className="text-left text-xs text-ink/70"><th scope="col" className="pr-3">Bottleneck</th><th scope="col" className="pr-3">What we saw</th><th scope="col">What we do about it</th></tr></thead>
            <tbody>
              {BOTTLENECKS.map(([a, b, c]) => (
                <tr key={a} className="border-t border-ink/10 align-top">
                  <th scope="row" className="py-2 pr-3 text-left font-semibold">{a}</th>
                  <td className="pr-3">{b}</td>
                  <td>{c}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
