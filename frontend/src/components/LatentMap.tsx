import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import type { Latent } from "../api";
import { SUBTYPE_COLORS } from "../api";
import { Card, ErrorNote, Skeleton } from "./Card";

const GROUPS = ["LumA", "LumB", "Basal", "Her2", "Normal", "Unknown"];

export function LatentMap({ latent, error }: { latent: Latent | null; error?: string | null }) {
  return (
    <Card title="Patient map" id="map-title" shadow="#D4E2FF"
      aside={<span className="text-xs text-ink/70">PCA of 198 proteins · filled = train, ring = locked test</span>}>
      {error ? <ErrorNote error={error} /> : !latent ? <Skeleton h="h-72" /> : (
        <>
          <div className="h-72 w-full" role="img"
            aria-label={`Scatter plot of ${latent.points.length} patients on the first two principal components, coloured by PAM50 subtype.`}>
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
                <CartesianGrid stroke="#eee" />
                <XAxis type="number" dataKey="x" tick={{ fontSize: 11 }}
                  label={{ value: `PC1 (${(latent.explained_variance[0] * 100).toFixed(0)}%)`, position: "insideBottom", offset: -8, fontSize: 11 }} />
                <YAxis type="number" dataKey="y" tick={{ fontSize: 11 }} width={36}
                  label={{ value: `PC2 (${(latent.explained_variance[1] * 100).toFixed(0)}%)`, angle: -90, position: "insideLeft", fontSize: 11 }} />
                <Tooltip cursor={false} formatter={(v: number) => v.toFixed(2)} />
                <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v: string) => <span style={{ color: "#111" }}>{v}</span>} verticalAlign="top" />
                {GROUPS.map((g) => {
                  const pts = latent.points.filter((p) => p.subtype === g);
                  if (!pts.length) return null;
                  const c = SUBTYPE_COLORS[g];
                  return (
                    <Scatter key={g} name={g} data={pts} fill={c} isAnimationActive={false}
                      shape={(props: { cx?: number; cy?: number; payload?: { split: string } }) => (
                        <circle cx={props.cx} cy={props.cy} r={props.payload?.split === "test" ? 3.5 : 2.5}
                          fill={props.payload?.split === "test" ? "white" : c} stroke={c} strokeWidth={1.5} opacity={0.85} />
                      )} />
                  );
                })}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-xs text-ink/70">{latent.method}. Shown for orientation; the panel model does not use these axes.</p>
        </>
      )}
    </Card>
  );
}
