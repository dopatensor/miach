import type { MarkerRow } from "../api";

/** All proteins as cells in rank order; brightness follows importance and the panel's k cells are lit. */
export function ProteinGrid({ markers, k, cols = 22 }: { markers: MarkerRow[]; k: number; cols?: number }) {
  const max = Math.max(...markers.map((m) => m.importance));
  return (
    <figure>
      <ol className="grid gap-[3px]" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
        aria-label={`${markers.length} proteins in rank order; the top ${k} form the candidate panel`}>
        {markers.map((m) => {
          const inPanel = m.rank <= k;
          const a = 0.16 + 0.6 * Math.sqrt(Math.max(0, m.importance) / max);
          return (
            <li key={m.protein} title={`#${m.rank} ${m.protein}`} className="aspect-square rounded-[3px]"
              style={inPanel ? { background: "var(--acc)" } : { background: "var(--fg)", opacity: a }}>
              <span className="sr-only">{m.rank}. {m.protein}{inPanel ? " (in panel)" : ""}</span>
            </li>
          );
        })}
      </ol>
      <figcaption className="mt-3 text-xs text-mute">
        {markers.length} proteins in rank order · brightness = importance ·{" "}
        <span className="text-acc">■</span> the {k}-marker candidate panel
      </figcaption>
    </figure>
  );
}
