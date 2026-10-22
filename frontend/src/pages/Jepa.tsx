import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, fmt, type Results } from "../api";
import { useAsync } from "../useAsync";
import { ErrorNote, Section, Skeleton } from "../components/Card";
import { Disclaimer } from "../components/Disclaimer";
import { row } from "./Results";

// Block names from ml/pathways.py (11 pathway blocks + "other"). n_mask_blocks = 3 in
// ml/encoders/transformer.py; which three are hidden here is illustrative.
const BLOCKS = ["hormone lineage", "rtk", "pi3k / mtor", "mapk", "dna repair", "cell cycle", "apoptosis",
  "adhesion / emt", "developmental", "metabolism / stress", "immune", "other"];
const HIDDEN = new Set(["pi3k / mtor", "cell cycle", "immune"]);
export const CODE_URL = "https://github.com/dopatensor/miach/blob/main/ml/encoders/transformer.py";

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
      <Box title="one patient">each measured protein is one token (protein identity + value); unmeasured proteins are left out</Box>
      <Down label="group into 11 pathway blocks + other; hide 3 whole blocks" />
      <ul className="grid grid-cols-2 gap-1 sm:grid-cols-4 lg:grid-cols-6" aria-label="Pathway blocks; three are hidden">
        {BLOCKS.map((b) => (
          <li key={b} className={`border px-2 py-1 text-center text-[11px] ${HIDDEN.has(b) ? "border-dashed border-acc text-fg" : "border-line text-mute"}`}>
            {HIDDEN.has(b) ? <>? {b}<span className="sr-only"> (hidden)</span></> : b}
          </li>
        ))}
      </ul>
      <div className="grid grid-cols-2 gap-3 pt-1">
        <div>
          <Down label="visible blocks only" />
          <Box title="context encoder">transformer over the visible proteins; this is what we keep</Box>
          <Down />
          <Box title="predictor">fills a query token at every hidden protein</Box>
          <Down />
          <Box title="predicted" dashed>embedding of each hidden block, not protein values</Box>
        </div>
        <div>
          <Down label="the whole patient" />
          <Box title="target encoder">slow moving-average (EMA) copy of the context encoder; no gradient</Box>
          <Down label="read out at the hidden blocks" />
          <Box title="actual" dashed>target embedding of each hidden block</Box>
        </div>
      </div>
      <Down label="average tokens within each hidden block, then compare" />
      <Box title="loss = mean squared error between block averages (predicted vs actual)" acc>
        updates the context encoder and predictor; the target encoder only drifts slowly toward the context encoder
      </Box>
      <figcaption id="jepa-caption" className="pt-2 text-[11px] text-mute">
        Pathway JEPA pretraining, one patient. Which three blocks are hidden is drawn at random per patient; the ones shown are an example.{" "}
        <a href={CODE_URL} target="_blank" rel="noreferrer" className="underline decoration-acc underline-offset-4 hover:text-fg">view code ↗</a>
      </figcaption>
    </figure>
  );
}

const NAMES: Record<string, string> = { brca: "breast", lung: "lung", crc: "colorectal" };
const list = (xs: string[]) => xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;

/** Elastic net vs JEPA at 10% and 100% labels, compared at the 2 decimals shown. */
function labelBudget(d: Results): string {
  const ids = Object.keys(NAMES);
  const v = (e: string, c: string, fr: number) => {
    const x = row(d, e, c, fr)?.macro_f1;
    return x == null ? null : Math.round(x * 100) / 100;
  };
  const lead10 = ids.filter((c) => (v("raw", c, 0.1) ?? -1) > (v("jepa", c, 0.1) ?? -1));
  const s10 = lead10.length === ids.length ? "At 10% labels the elastic net leads all three."
    : `At 10% labels the elastic net leads on ${list(lead10.map((c) => NAMES[c])) || "none"}.`;
  const ties = ids.filter((c) => v("raw", c, 1) != null && v("raw", c, 1) === v("jepa", c, 1));
  const jepaWins = ids.filter((c) => (v("jepa", c, 1) ?? -1) > (v("raw", c, 1) ?? -1));
  const rawWins = ids.filter((c) => !ties.includes(c) && !jepaWins.includes(c));
  const parts = [
    ...ties.map((c) => `JEPA ties it on ${NAMES[c]}, ${fmt(v("jepa", c, 1))}`),
    ...jepaWins.map((c) => `JEPA leads on ${NAMES[c]}, ${fmt(v("jepa", c, 1))} vs ${fmt(v("raw", c, 1))}`),
  ];
  const s100 = parts.length
    ? `With all labels ${parts.join("; ")}${rawWins.length ? `; the elastic net still leads on ${list(rawWins.map((c) => NAMES[c]))}` : ""}.`
    : "With all labels the elastic net still leads all three.";
  return `${s10} ${s100}`;
}

const MEASURED = [["brca", "breast"], ["lung", "lung"], ["crc", "colorectal"]] as const;

function Measured({ d }: { d: Results }) {
  const f = (enc: string, c: string) => row(d, enc, c, 0.1)?.macro_f1 ?? null;
  const h = d.health;
  const rows = MEASURED.map(([id, name]) => ({ name, j: f("jepa", id), r: f("recon", id), raw: f("raw", id) }));
  const won = rows.filter((x) => x.j != null && x.r != null && x.j > x.r).map((x) => x.name);
  const lost = rows.filter((x) => x.j != null && x.r != null && x.j <= x.r).map((x) => x.name);
  const budget = labelBudget(d);
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
        {" "}{budget}
      </p>
      {h.jepa && h.recon && (
        <p className="mt-2 text-[11px] text-mute">
          Embedding health (breast locked test set): JEPA relative spread {h.jepa.rel_std.toFixed(3)} vs{" "}
          {h.recon.rel_std.toFixed(2)} for the reconstruction control; effective rank {h.jepa.eff_rank.toFixed(0)} of {h.jepa.dim}.
          The code flags collapse below 0.01 and expects about 0.05–0.3 for a healthy transformer, so JEPA is close to
          collapse{h.jepa.collapsed ? " (flagged)" : " but not flagged"}.
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
            <p>A reconstruction model must rebuild every hidden protein level, including assay noise it can never predict.</p>
            <p>JEPA predicts the hidden blocks' embedding from a slowly updated target encoder instead, so noise it can't predict is
              free to ignore. To do that from the other pathways it has to learn how pathways relate to each other.</p>
            <p>The reconstruction control is the same transformer with the same inputs and masks, trained to predict the hidden raw
              values. The gap between the two isolates the JEPA objective.</p>
          </div>
        </Section>
        <Section index={3} title="after pretraining" id="after-title">
          <div className="space-y-2 text-mute">
            <p>The predictor and the target encoder are thrown away. The context encoder is frozen and now sees every measured protein.</p>
            <p>Each patient becomes one embedding: the average of its protein tokens. A small linear model is fitted on those embeddings with 10% or 100% of the
              training labels, then scored once on the locked test set.</p>
            <p>Pretraining used a pan-cancer pool that excludes the locked test patients of all four cancers.</p>
          </div>
        </Section>
        <Section index={4} title="what we measured" id="measured-title">
          {error ? <ErrorNote error={error} /> : !data ? <Skeleton h="h-40" /> : <Measured d={data} />}
        </Section>
      </div>

      <p className="text-[11px] text-mute">
        Full comparison across five models and four cancers: <Link to="/results" className="underline decoration-acc underline-offset-4 hover:text-fg">results</Link>
        {" "}· <a href={CODE_URL} target="_blank" rel="noreferrer" className="underline decoration-acc underline-offset-4 hover:text-fg">view code: ml/encoders/transformer.py ↗</a>
      </p>
      <Disclaimer compact />
    </div>
  );
}
