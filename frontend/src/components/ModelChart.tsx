import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Models } from "../api";
import { Card, ErrorNote, Skeleton } from "./Card";

const C10 = "#D9682F";
const C100 = "#4057C0";

export function ModelChart({ models, error }: { models: Models | null; error?: string | null }) {
  return (
    <Card title="Six-model comparison" id="models-title"
      aside={<span className="chip bg-sun">Locked test · n = 176 · preliminary</span>}>
      {error ? <ErrorNote error={error} /> : !models ? <Skeleton h="h-80" /> : (
        <>
          <p className="mb-2 text-sm">{models.metric}, training with 10% or 100% of the training labels.</p>
          <div className="h-80 w-full" role="img" aria-label="Bar chart of subtype macro-F1 per model; values in the table below.">
            <ResponsiveContainer>
              <BarChart data={models.models} layout="vertical" margin={{ top: 4, right: 36, left: 8, bottom: 4 }} barGap={2}>
                <CartesianGrid horizontal={false} stroke="#eee" />
                <XAxis type="number" domain={[0, 0.8]} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="model" width={150} tick={{ fontSize: 11, fill: "#111" }} />
                <Tooltip formatter={(v: number) => v.toFixed(2)} cursor={{ fill: "#D4E2FF", opacity: 0.4 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v: string) => <span style={{ color: "#111" }}>{v}</span>} verticalAlign="top" />
                <Bar dataKey="f1_10" name="10% labels" fill={C10} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  <LabelList dataKey="f1_10" position="right" fontSize={10} fill="#111" formatter={(v: number) => v.toFixed(2)} />
                </Bar>
                <Bar dataKey="f1_100" name="100% labels" fill={C100} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  <LabelList dataKey="f1_100" position="right" fontSize={10} fill="#111" formatter={(v: number) => v.toFixed(2)} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="mt-3 w-full text-sm">
            <caption className="mb-1 text-left text-xs text-ink/70">Table view · {models.source}</caption>
            <thead><tr className="text-left text-xs text-ink/70">
              <th scope="col">Model</th><th scope="col">Type</th><th scope="col">10% labels</th><th scope="col">100% labels</th>
            </tr></thead>
            <tbody>
              {models.models.map((m) => (
                <tr key={m.model} className={`border-t border-ink/10 ${m.production ? "font-semibold" : ""}`}>
                  <td className="py-1">{m.model}{m.production && <span className="chip ml-2 bg-sun">production</span>}</td>
                  <td>{m.kind === "deep" ? "deep (research)" : "linear"}</td>
                  <td className="tabular-nums">{m.f1_10.toFixed(2)}</td>
                  <td className="tabular-nums">{m.f1_100.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink/70">
            This site's rebuild of the elastic net (own patient-level split, 100% labels) scores{" "}
            {models.rebuild_check.macro_f1.toFixed(3)} on its locked test set.
          </p>
        </>
      )}
    </Card>
  );
}
