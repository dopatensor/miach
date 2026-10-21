import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, fmt } from "../api";
import { useAsync } from "../useAsync";
import { Section, Skeleton } from "../components/Card";
import { Disclaimer } from "../components/Disclaimer";

const EXAMPLE_K = 8;

function Step({ index, title, children }: { index: number; title: string; children: ReactNode }) {
  return (
    <Section index={index} title={title} id={`how-${index}`}>
      <div className="max-w-3xl space-y-2 text-mute">{children}</div>
    </Section>
  );
}

const GLOSSARY: [string, string][] = [
  ["protein marker", "One protein whose level is measured in a tumour sample. A panel is a short list of them."],
  ["subtype", "A group of breast tumours that behave alike. Here: the five PAM50 groups LumA, LumB, Basal, Her2 and Normal-like."],
  ["macro-F1", "How well the panel sorts tumours into subtypes, averaged so each subtype counts equally. 1.0 is perfect."],
  ["C-index", "How well the score orders patients by how soon their cancer progressed. 0.5 is a coin flip, 1.0 is perfect."],
  ["locked test set", "Patients set aside at the start and used only once, for the final score. Nothing is tuned on them."],
  ["preliminary", "One public cohort, one split, no outside validation yet. Treat the numbers as a first estimate."],
];

export function HowItWorks() {
  const qc = useAsync(() => api.qc());
  const panel = useAsync(() => api.panel(EXAMPLE_K));
  const s = qc.data?.splits;
  return (
    <div className="space-y-8">
      <header className="max-w-3xl space-y-1">
        <h1 className="text-lg font-bold">how it works · in plain English</h1>
        <p className="text-mute">No biology background needed. This is what happens between the raw data and the panel card.</p>
      </header>

      <Step index={1} title="the problem">
        <p>Big research assays can measure hundreds of proteins in a tumour. A routine hospital lab can usually measure only a handful
          per sample, with cheap tests such as staining a tissue slide (IHC) or counting RNA copies (qPCR).</p>
        <p className="text-fg">So the question is: which few proteins carry most of the information?</p>
      </Step>

      <Step index={2} title="the data">
        {!qc.data ? <Skeleton h="h-10" /> : (
          <p>Public breast tumours from The Cancer Genome Atlas, each with {qc.data.n_proteins} protein levels. Before anything is learned, the
            patients are split once: {s!.train.patients} to learn from, {s!.val.patients} to make choices with, and{" "}
            <span className="text-fg">{s!.test.patients} locked away</span> for the final score.</p>
        )}
      </Step>

      <Step index={3} title="learn">
        <p>A simple statistical model (an elastic net, a cautious kind of regression) learns to tell the breast cancer subtypes apart
          from all the proteins at once, using the learning patients only.</p>
        <p>We also tried deep-learning models. With only a few hundred labelled patients the simple model won, so it is the one used
          here. <Link to="/evidence" className="underline decoration-acc underline-offset-4 hover:text-fg">see the comparison</Link></p>
      </Step>

      <Step index={4} title="rank">
        <p>To find out which proteins matter, we hide each protein in turn (replace it with an average value) and measure how much
          worse the model gets. A big drop means an important protein.</p>
        <p>We repeat this on many reshuffled copies of the learning patients. A protein that keeps coming out near the top is
          <span className="text-fg"> stable</span>; one that only ranks high once is probably luck.</p>
      </Step>

      <Step index={5} title="choose a budget">
        <p>You pick how many markers you can afford with the slider. We take that many from the top of the ranking, fit a small model
          on just those, and score it once on the locked patients.</p>
        {!panel.data ? <Skeleton h="h-10" /> : (
          <p>Example: with {EXAMPLE_K} markers the panel scores macro-F1 <span className="text-fg">{fmt(panel.data.metrics.macro_f1)}</span>,
            against {fmt(panel.data.full_model.metrics.macro_f1)} for a model using all {panel.data.full_model.k} proteins
            (locked test set, n = {panel.data.test_n}, preliminary).</p>
        )}
        <p>All of this is computed in advance, which is why moving the slider is instant.{" "}
          <Link to="/designer" className="underline decoration-acc underline-offset-4 hover:text-fg">try the designer</Link></p>
      </Step>

      <Step index={6} title="what it is not">
        <p>It is a research tool for choosing candidate markers to test further. It does not diagnose anyone or suggest treatment,
          and its numbers come from one public dataset.</p>
      </Step>

      <Section index={7} title="glossary" id="how-glossary">
        <dl className="grid max-w-4xl gap-x-6 gap-y-3 sm:grid-cols-[12rem_1fr]">
          {GLOSSARY.map(([t, d]) => (
            <div key={t} className="contents">
              <dt className="text-fg">{t}</dt>
              <dd className="text-mute">{d}</dd>
            </div>
          ))}
        </dl>
      </Section>
      <Disclaimer compact />
    </div>
  );
}
