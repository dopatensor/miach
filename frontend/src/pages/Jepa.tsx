import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, fmt, type Results } from "../api";
import { useAsync } from "../useAsync";
import { ErrorNote, Section, Skeleton } from "../components/Card";
import { Disclaimer } from "../components/Disclaimer";
import { row } from "./Results";

// Illustration only: eight pathway blocks from ml/pathways.py, two of them hidden.
const BLOCKS = ["hormone receptor", "RTK", "PI3K/AKT", "TSC/mTOR", "RAS/MAPK", "cell cycle", "DNA damage", "apoptosis"];
const HIDDEN = new Set(["PI3K/AKT", "cell cycle"]);

function Box({ title, children, dashed = false, acc = false }: { title: string; children?: ReactNode; dashed?: boolean; acc?: boolean }) {
  return (
    <div className={`border px-3 py-2 ${dashed ? "border-dashed" : ""} ${acc ? "border-acc" : "border-line"}`}>
      <div className="text-fg">{title}</div>
      {children && <div className="mt-0.5 text-[11px] text-mute">{children}</div>}
    </div>
  );
}

function Down({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-1 pl-4 text-[11px] text-mute" aria-hidden="true">
      <span className="text-fg">↓</span>{label}
    </div>
  );
}

function Diagram() {
  return (
    <figure aria-labelledby="jepa-caption" className="space-y-1">
      <Box title="one patient">198 protein levels, grouped into pathway blocks</Box>
      <Down />
      <ul className="grid grid-cols-2 gap-1 sm:grid-cols-4 lg:grid-cols-8" aria-label="Pathway blocks; two are hidden">
        {BLOCKS.map((b) => (
          <li key={b} className={`border px-2 py-1 text-center text-[11px] ${HIDDEN.has(b) ? "border-dashed border-acc text-fg" : "border-line text-mute"}`}>
            {HIDDEN.has(b) ? <>? {b}<span className="sr-only"> (hidden)</span></> : b}
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-2 gap-3 pt-1">
        <div>
          <Down label="visible blocks" />
          <Box title="context encoder">learns; this is what we keep</Box>
          <Down />
          <Box title="predictor">guesses the hidden blocks' summary</Box>
          <Down />
          <Box title="predicted" dashed>a summary vector, not protein values</Box>
        </div>
        <div>
          <Down label="hidden blocks" />
          <Box title="target encoder">slow moving-average (EMA) copy of the context encoder; no gradient</Box>
          <Down />
          <Box title="actual" dashed>the hidden blocks' real summary vector</Box>
        </div>
      </div>
      <Down label="compare" />
      <Box title="loss = distance(predicted, actual)" acc>
        updates the context encoder and predictor; the target encoder only drifts slowly toward the context encoder
      </Box>
      <figcaption id="jepa-caption" className="pt-2 text-[11px] text-mute">
        Pathway JEPA pretraining, one patient. Illustrative: which blocks are hidden changes from step to step.
      </figcaption>
    </figure>
  );
}

const MEASURED = [["brca", "breast"], ["lung", "lung"], ["crc", "colorectal"]] as const;

function Measured({ d }: { d: Results }) {
  const f = (enc: string, c: string) => row(d, enc, c, 0.1)?.macro_f1 ?? null;
  const h = d.health;
  const rows = MEASURED.map(([id, name]) => ({ name, j: f("jepa", id), r: f("recon", id), raw: f("raw", id) }));
  const won = rows.filter((x) => x.j != null && x.r != null && x.j > x.r).map((x) => x.name);
  const lost = rows.filter((x) => x.j != null && x.r != null && x.j <= x.r).map((x) => x.name);
  const rawAhead = rows.every((x) => x.j != null && x.raw != null && x.raw > x.j);
  return (
    <>
      <p className="mb-3">JEPA minus the reconstruction control, macro-F1 with 10% of training labels:</p>
      <table className="w-full">
        <caption className="sr-only">JEPA minus reconstruction control at 10% labels, per cancer</caption>
        <thead><tr className="text-left text-[11px] text-mute"><th scope="col">cancer</th><th scope="col" className="text-right">JEPA</th><th scope="col" className="text-right">recon</th><th scope="col" className="text-right">Δ</th><th scope="col" className="text-right">elastic net</th></tr></thead>
        <tbody>
          {rows.map(({ name, j, r, raw }) => {
            const delta = j != null && r != null ? j - r : null;
            return (
              <tr key={name} className="border-t border-line tabular-nums">
                <th scope="row" className="py-1 text-left font-normal">{name}</th>
                <td className="text-right text-mute">{fmt(j)}</td>
                <td className="text-right text-mute">{fmt(r)}</td>
                <td className="text-right font-bold text-fg">{delta == null ? "—" : `${delta >= 0 ? "+" : "−"}${Math.abs(delta).toFixed(2)}`}</td>
                <td className="text-right text-mute">{fmt(raw)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-mute">
        Predicting meaning beat predicting values on {won.join(" and ") || "no cancer"}
        {lost.length > 0 && <>, not on {lost.join(" and ")}</>}.
        {rawAhead && " The plain elastic net on raw proteins is still ahead of JEPA with 10% labels in all three, which is why the Designer uses it."}
      </p>
      {h.jepa && h.recon && (
        <p className="mt-2 text-[11px] text-mute">
          Embedding health (breast locked test set): JEPA effective rank {h.jepa.eff_rank.toFixed(0)} of {h.jepa.dim} dimensions,
          embedding spread {h.jepa.emb_std.toFixed(3)} vs {h.recon.emb_std.toFixed(2)} for the reconstruction control
          ({h.recon.dim} dimensions). A tiny spread is an early sign of collapse, the failure JEPA training has to fight.
        </p>
      )}
      <p className="mt-2 text-[11px] text-mute">locked test set · preliminary · source: four-cancer run</p>
    </>
  );
}

export function Jepa() {
  const { data, error } = useAsync(() => api.results());
  return (
    <div className="space-y-8">
      <header className="max-w-3xl space-y-1">
        <h1 className="text-lg font-bold">pathway JEPA · research track</h1>
        <p className="text-mute">
          A self-supervised encoder that learns from unlabelled tumours by hiding whole pathways and predicting
          what they mean. It is not used in the Designer; this page shows how it works and what it achieved.
        </p>
      </header>

      <Section index={1} title="how pretraining works" id="jepa-diagram-title">
        <Diagram />
      </Section>

      <div className="grid gap-6 lg:grid-cols-3">
        <Section index={2} title="why predict meaning, not values" id="why-title">
          <div className="space-y-2 text-mute">
            <p>A reconstruction model must rebuild every protein level, including assay noise, so much of what it learns is noise.</p>
            <p>JEPA only has to predict a compact summary of the hidden pathways. To do that from the other pathways it has to learn how
              pathways relate to each other, which is closer to the biology a classifier needs.</p>
            <p>The reconstruction control is trained to rebuild the raw protein values instead, so the gap between the two shows what predicting meaning adds.</p>
          </div>
        </Section>
        <Section index={3} title="after pretraining" id="after-title">
          <div className="space-y-2 text-mute">
            <p>The predictor and the target encoder are thrown away. The context encoder is frozen and now sees all pathways.</p>
            <p>Each patient becomes one embedding. A small linear model is fitted on those embeddings with 10% or 100% of the
              training labels, then scored once on the locked test set.</p>
            <p>Pretraining used a pan-cancer pool that excludes the locked test patients of all four cancers.</p>
          </div>
        </Section>
        <Section index={4} title="what we measured" id="measured-title">
          {error ? <ErrorNote error={error} /> : !data ? <Skeleton h="h-40" /> : <Measured d={data} />}
        </Section>
      </div>

      <p className="text-[11px] text-mute">
        Full comparison across five models and four cancers: <Link to="/results" className="underline decoration-acc underline-offset-4 hover:text-fg">results</Link>.
      </p>
      <Disclaimer compact />
    </div>
  );
}
