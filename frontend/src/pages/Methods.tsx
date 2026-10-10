import type { ReactNode } from "react";
import { api } from "../api";
import { useAsync } from "../useAsync";

export function Methods() {
  const health = useAsync(() => api.health());
  return (
    <article className="max-w-3xl space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Methods</h1>
        <p className="text-sm text-ink/70">Artifacts built {health.data?.artifacts_built_at ?? "…"}.</p>
      </header>
      <Section title="Data">
        <p>TCGA PanCancer Atlas breast invasive carcinoma (BRCA), reverse-phase protein array (RPPA), 198 proteins and
          phospho-proteins, downloaded from the cBioPortal datahub (<code>brca_tcga_pan_can_atlas_2018</code>). Labels: PAM50
          subtype (LumA, LumB, Basal, Her2, Normal) and progression-free survival from the TCGA clinical data.</p>
      </Section>
      <Section title="Split and preprocessing">
        <p>Patients are split once with a fixed seed into training (595), validation (105) and a locked test set (176).
          Missing values are filled with the training-set median, then each protein is z-scored with training-set mean and
          standard deviation. Uploaded data is transformed with the same stored parameters.</p>
      </Section>
      <Section title="Model">
        <p>Production model: multinomial logistic regression with an elastic-net penalty (L1 ratio 0.5, class-balanced) on all
          198 proteins. Regularisation strength is chosen on the validation split, then the model is refit on training +
          validation.</p>
      </Section>
      <Section title="Marker ranking">
        <p>Occlusion importance: for each protein, the drop in the model's mean log-probability of the true subtype when that
          protein is set to its training mean. We refit the elastic net on 20 bootstrap resamples of the training patients and
          score each on its out-of-bag patients plus the validation split. Importance is the mean (± sd) over refits; stability
          is the share of refits that place the protein in the top 8.</p>
        <p>Correlated proteins share credit: when two markers carry the same signal, removing one costs little, so both can rank
          lower than their biology suggests (PR versus ER-alpha is the clearest case).</p>
      </Section>
      <Section title="Panels and metrics">
        <p>For each budget k = 1…30 the top-k proteins feed a small L2 logistic regression (strength chosen on validation, refit on
          training + validation) that is scored once on the locked test set. Metrics: macro-F1 and balanced accuracy over the five
          subtypes, macro one-vs-rest AUROC, and Harrell's C-index for progression-free survival.</p>
        <p>The C-index uses a subtype-derived risk score: predicted subtype probabilities weighted by each subtype's progression
          rate in the training set. It is not a survival-optimised panel; that ranking is not built yet.</p>
      </Section>
      <Section title="Limitations">
        <ul className="list-disc space-y-1 pl-5">
          <li>One cohort and one split; no external validation. All numbers are preliminary.</li>
          <li>Protein only. PAM50 is RNA-defined, which caps protein-only accuracy. RNA and multi-omics fusion are in development and not part of the live engine.</li>
          <li>23 progression events in the test set: survival metrics have wide uncertainty.</li>
          <li>RPPA values are not directly transferable to IHC or qPCR read-outs; a panel needs assay-specific validation.</li>
          <li>Research use only. Not for diagnosis or treatment decisions.</li>
        </ul>
      </Section>
      <Section title="References">
        <ul className="list-disc space-y-1 pl-5">
          <li>Hoadley KA et al. Cell-of-origin patterns dominate the molecular classification of 10,000 tumors from 33 types of cancer. <em>Cell</em> 2018.</li>
          <li>Akbani R et al. A pan-cancer proteomic perspective on The Cancer Genome Atlas. <em>Nat Commun</em> 2014.</li>
          <li>Parker JS et al. Supervised risk predictor of breast cancer based on intrinsic subtypes (PAM50). <em>J Clin Oncol</em> 2009.</li>
          <li>Cerami E et al. The cBio Cancer Genomics Portal. <em>Cancer Discov</em> 2012.</li>
          <li>Zou H, Hastie T. Regularization and variable selection via the elastic net. <em>JRSS B</em> 2005.</li>
        </ul>
      </Section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xl font-bold text-navy">{title}</h2>
      <div className="space-y-2 leading-relaxed">{children}</div>
    </section>
  );
}
