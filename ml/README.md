# Multi-omics biomarker MVP: standard baseline vs pathway JEPA

Protein-only (RPPA) comparison on TCGA breast cancer, to decide which encoder the full
product is built around. Data downloads automatically from the public cBioPortal datahub;
no account needed.

## What it compares

| Key | Encoder | Role |
|---|---|---|
| `raw` | Raw proteins + elastic-net probe | Strong simple baseline |
| `pca` | PCA (32-d), fitted on the pan-cancer pool | Linear floor the deep models must beat |
| `vae` | VAE pretrained on all 31 TCGA cancer types | Unsupervised deep baseline |
| `vae_joint` | Same VAE fine-tuned on breast cancer with subtype + Cox survival heads | **The deck's standard base** |
| `recon` | Pathway-masked transformer, predicts hidden **values** | Control that isolates the JEPA objective |
| `jepa` | Same transformer, predicts hidden pathways' **embeddings** (EMA target) | The candidate |

Every encoder implements one interface (`encoders/base.py`): `fit(ds, labelled_idx, seed)` and
`embed(X)`. Evaluation, marker ranking and the panel refit only use that interface, so the
losing encoder can be deleted without touching anything else.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python data.py                                  # download + build the dataset (~10 s), prints a summary
python run_compare.py --encoders raw,pca        # classic baselines only, no PyTorch needed
python run_compare.py --quick                   # all six encoders, 8 cancer types, 3 epochs, 2 seeds
python run_compare.py --threads 8               # full run (31 cancer types, 30 epochs, 5 seeds)
python run_compare.py --encoder-seeds 3         # final run: averages over 3 pretrained copies
```

Useful flags: `--encoders jepa,recon,pca` (subset), `--epochs 50` (transformer epochs),
`--panel ""` (skip marker ranking, which is the slowest step), `--fractions 0.1,1.0`.

JEPA experiments without editing code: `--tf-opt KEY=VALUE`, repeatable. Settings live in
`TransformerSSLEncoder._defaults()`, e.g.

```bash
python run_compare.py --encoders pca,recon,jepa --panel "" --tf-opt n_mask_blocks=4 --tf-opt target=token
```

**Runtime.** The transformers dominate. On a 2-core CPU one epoch over the quick subset
(~3,000 tumours) takes about 2.5 minutes, and JEPA marker ranking about 3 minutes per bootstrap.
A full run on a laptop CPU takes hours, so use a GPU if you can: training picks up CUDA or
Apple Silicon (MPS) automatically. Free Colab GPUs work fine. The VAEs and classic models
take seconds to minutes.

## Outputs (`results/`)

| File | Contents |
|---|---|
| `summary.md` | Go/no-go verdict, all metrics with 95% CIs, representation health, marker panels |
| `metrics.csv` | Every encoder × label fraction × seed |
| `summary.csv` | Seed-averaged metrics with bootstrap CIs |
| `markers_<encoder>.csv` | Protein ranking: importance, SD, bootstrap stability, pathway |
| `panel_<encoder>.csv` | Top-k raw-protein panels refit on train, scored on test |
| `training_logs.json` | Per-epoch loss and collapse diagnostics |

## How the evaluation works

- **Locked split.** 20% of breast cancer patients form a test set (stratified by subtype, fixed
  seed) that is never used for training, pretraining, model selection or marker selection.
- **Label budgets.** Probes see 10%, 25% or 100% of training labels. Self-supervised methods
  usually show their advantage when labels are scarce.
- **Probes.** Every encoder is frozen; a logistic regression (subtype, C chosen by CV) and a ridge
  Cox model (progression-free survival) are fitted on its embeddings.
- **Metrics.** Macro-F1 and balanced accuracy for PAM50 subtype (classes are imbalanced);
  Harrell's C-index for survival. 95% CIs come from bootstrapping test patients.
- **Go/no-go.** JEPA must beat both PCA and the reconstruction control at the lowest label budget
  (paired bootstrap on macro-F1) without collapsing.
- **Collapse.** `rel_std` (spread across patients, scale-free) and effective rank of the
  embeddings, logged every epoch. Collapse means `rel_std` < 0.01 or effective rank < 2.
- **Markers.** Occlusion importance: how much worse the subtype prediction gets when one protein
  is treated as unmeasured, on out-of-bag patients across bootstrap resamples of the training set.

## Known limitations

- **Survival is underpowered.** The test set has only 23 progression events, so C-index
  intervals are wide. Treat subtype as the primary decision metric.
- **Correlated markers share credit.** Occlusion importance under-ranks a protein whose
  information is duplicated by another (e.g. PR alongside ER). Read stability alongside rank.
- **Proteins only.** This is deliberately one layer. Multi-omics fusion (Product-of-Experts)
  comes after the encoder decision, when RNA is added.
- **PAM50 labels come from RNA**, not protein, so protein-only accuracy has a ceiling.

## Files

```
config.py          paths, splits, label fractions, known markers
data.py            download, patient matching, locked splits, z-scoring
pathways.py        protein -> pathway blocks (what the JEPA masks)
evaluate.py        probes, Cox, C-index, bootstrap, collapse stats
encoders/          base interface + classic, vae, transformer (jepa/recon)
panel.py           marker ranking and small-panel refit
run_compare.py     orchestrates everything and writes results/
```
