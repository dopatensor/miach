import { ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { useNavigate } from "react-router-dom";
import type { Latent, LatentPoint } from "../api";
import { SUBTYPES } from "../api";
import { ErrorNote, Skeleton } from "./Card";
import { centroids, domain } from "./mapUtils";

const GROUPS = [...SUBTYPES, "Unknown"];
const axis = { fontSize: 11, fill: "var(--mute)", fontFamily: "inherit" };

export function LatentMap({ latent, error }: { latent: Latent | null; error?: string | null }) {
  const navigate = useNavigate();
  if (error) return <ErrorNote error={error} />;
  if (!latent) return <Skeleton h="h-72" />;
  const xd = domain(latent.points.map((p) => p.x));
  const yd = domain(latent.points.map((p) => p.y));
  const open = (p: LatentPoint) => p.id && navigate(`/patients?id=${encodeURIComponent(p.id)}`);
  return (
    <div>
      <ul className="mb-2 flex flex-wrap gap-x-4 text-[11px] text-mute" aria-label="Legend">
        {GROUPS.map((g) => (
          <li key={g}><span aria-hidden="true" className="mr-1.5 inline-block h-2 w-2" style={{ background: `var(--c-${g})` }} />{g.toLowerCase()}</li>
        ))}
        <li className="ml-auto">dot = train · ring = locked test (click to open) · view clipped to central 98%</li>
      </ul>
      <div className="h-72 w-full" role="img"
        aria-label={`Scatter plot of ${latent.points.length} patients on the first two principal components, coloured by PAM50 subtype.`}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
            <XAxis type="number" dataKey="x" tick={axis} stroke="var(--line)" tickLine={false} domain={xd} allowDataOverflow
              label={{ value: `pc1 ${(latent.explained_variance[0] * 100).toFixed(0)}%`, position: "insideBottomRight", ...axis }} />
            <YAxis type="number" dataKey="y" tick={axis} stroke="var(--line)" tickLine={false} width={32} domain={yd} allowDataOverflow />
            <Tooltip cursor={false} content={({ payload }) => {
              const p = payload?.[0]?.payload as LatentPoint | undefined;
              if (!p) return null;
              return <div className="border border-line bg-bg px-2 py-1 text-[11px]">{p.id ?? "training patient"} · {p.subtype}</div>;
            }} />
            {GROUPS.map((g) => {
              const pts = latent.points.filter((p) => p.subtype === g);
              if (!pts.length) return null;
              const c = `var(--c-${g})`;
              return (
                <Scatter key={g} name={g} data={pts} isAnimationActive={false} onClick={(d: { payload?: LatentPoint }) => d.payload && open(d.payload)}
                  shape={(props: { cx?: number; cy?: number; payload?: LatentPoint }) => props.payload?.split === "test"
                    ? <circle cx={props.cx} cy={props.cy} r={3.5} style={{ fill: "var(--bg)", stroke: c, cursor: "pointer" }} strokeWidth={1.5} />
                    : <circle cx={props.cx} cy={props.cy} r={2} style={{ fill: c }} />} />
              );
            })}
            <Scatter data={centroids(latent.points, (xd[1] - xd[0]) * 0.07)} isAnimationActive={false} legendType="none"
              shape={(props: { cx?: number; cy?: number; payload?: { subtype: string; dy: number } }) => (
                <text x={props.cx} y={(props.cy ?? 0) + (props.payload?.dy ?? -10)} textAnchor="middle" fontSize={12} fill="var(--fg)"
                  stroke="var(--bg)" strokeWidth={4} paintOrder="stroke" pointerEvents="none">{props.payload?.subtype}</text>
              )} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[11px] text-mute">{latent.method.toLowerCase()}. for orientation only; the panel model does not use these axes.</p>
    </div>
  );
}
