# CLAUDE.md — Miach: biomarker panel designer (hackathon build)

## What we are building

A website (**miach.online**) where a researcher picks a disease, a goal and a marker budget, and gets a
small, assay-ready **biomarker panel** with its validated performance and evidence. The engine turns
multi-omics data into a few markers a cheap lab test (IHC / qPCR) could measure.

- **Hackathon:** Zéphyr 2026 AI Hackathon, problem statement "Accelerating Multi-Omics Data Integration
  and Predictive Biomarker Discovery for Precision Medicine". **One week. Demo first.**
- **Users:** translational researchers, bioinformaticians, clinician-scientists. Not patients.
- **Research use only.** Never present output as a diagnosis or treatment advice. Show this in the UI footer
  and on every result card.
- **Naming:** the product is **Miach** (domain miach.online). The pitch deck may still say "FuseOmics";
  don't introduce a third name.

## Ground truth: what works today

Everything below was measured with the `omics_mvp` pipeline on public TCGA data. Keep the website's numbers
consistent with these, and label them **preliminary** until a full run replaces them.

- **Data:** TCGA PanCancer Atlas protein (RPPA) data from the cBioPortal datahub. 198 proteins.
  Pretraining pool: 7,084 tumours from 31 cancer types. Breast cancer split (patient-level, fixed seed):
  595 train · 105 val · **176 locked test**. Labels: PAM50 subtype (LumA, LumB, Basal, Her2, Normal),
  progression-free survival (only 23 test events).
- **Subtype macro-F1 on the locked test set** (10% labels / 100% labels):
  elastic net 0.56 / 0.63 · PCA 0.52 / 0.59 · VAE 0.49 / 0.55 · VAE + heads 0.47 / 0.56 ·
  reconstruction control 0.32 / 0.58 · pathway JEPA 0.39 / 0.57.
- **Production model = elastic net on raw proteins.** It won. Deep models (VAE, JEPA) are a research track:
  show them on the Evidence page, never in the main product flow.
- **Marker ranking** (occlusion importance + bootstrap stability) recovers known drivers:
  ER-alpha #1, HER2 #5, GATA3 #7 of 198. PR ranks low because ER carries the same signal; say so in the UI.
- **Known bottlenecks** (show honestly on the Evidence page): small data favours simple models; protein-only
  ceiling (PAM50 is RNA-defined); survival underpowered (23 events); JEPA shortcut/dimensional collapse;
  correlated markers share credit; pretrained-model leakage and licence risks.

## Architecture

```
            OFFLINE (run once, ~minutes)                         ONLINE (every request, < 300 ms)
┌──────────────────────────────────────────────┐      ┌─────────────────────────────────────────────┐
│ ml/build_artifacts.py                         │      │ backend (FastAPI)                            │
│  data.build_dataset()  → splits, z-scores     │      │  loads artifacts/ at startup (read-only)     │
│  elastic net fit       → model.joblib         │ ───► │  /api/...  serves JSON from memory           │
│  rank_markers(raw)     → markers.json         │      │  panel refit for an uncached k: tiny LR      │
│  evaluate_panels(k=1..30) → panels.json       │      └───────────────────────┬─────────────────────┘
│  2-D map (PCA)          → latent.json         │                              │ JSON
│  QC + comparison table  → qc.json, models.json│      ┌───────────────────────▼─────────────────────┐
└──────────────────────────────────────────────┘      │ frontend (React + Vite + TS)                 │
                                                       │  Landing · Designer · Patients · Evidence    │
                                                       └─────────────────────────────────────────────┘
```

**The one rule that makes it feel live:** never train anything at request time. Everything slow is
precomputed into `artifacts/`. The marker-budget slider reads precomputed panels for k = 1..30; only an
unusual request (e.g. a custom marker list) triggers a refit, which is a logistic regression on ≤ 30
features and takes milliseconds.

### Stack (decided; don't re-litigate)

| Layer | Choice | Why |
|---|---|---|
| ML | Python 3.11+, numpy, pandas, scikit-learn, scipy (from `omics_mvp`) | Already works and tested |
| Backend | FastAPI + Pydantic v2, uvicorn | Typed contract, auto docs at `/docs` |
| Frontend | React 18 + Vite + TypeScript, Tailwind, Recharts | Fast to build; charts without heavy deps |
| PDF export | Print stylesheet + `window.print()` | Zero backend work |
| Deploy | One Docker image: FastAPI serves the built frontend from `/` and the API from `/api` | One service, one domain |
| Hosting | Azure Container Apps (Microsoft hackathon) with miach.online as a custom domain; Render or Fly as fallback | |

PyTorch is **not** a backend dependency. Only `ml/` research scripts use it.

## Repository layout

```
miach/
├── CLAUDE.md
├── ml/                      # copied from omics_mvp/ (config, data, pathways, evaluate, panel, encoders/)
│   ├── build_artifacts.py   # NEW: produces everything in artifacts/
│   └── run_compare.py       # research comparison (unchanged)
├── artifacts/               # generated JSON + model.joblib; commit these so deploys need no data download
├── backend/
│   ├── app/main.py          # FastAPI app, CORS, static mount of frontend/dist
│   ├── app/schemas.py       # Pydantic models = the API contract below
│   ├── app/store.py         # loads artifacts once at startup
│   ├── app/routers/         # dataset.py, markers.py, panel.py, models.py, predict.py
│   └── tests/
├── frontend/
│   ├── src/pages/           # Landing, Designer, Patients, Evidence (+ Methods section)
│   ├── src/components/      # PanelCard, MarkerList, LatentMap, QcCard, ModelChart, Disclaimer
│   └── src/api.ts           # typed client generated from /openapi.json or hand-written to match schemas
└── Dockerfile
```

## `ml/build_artifacts.py` (write this first)

Reuse the `omics_mvp` APIs exactly as they are:

```python
import data, evaluate as E
from encoders import get_encoder
from panel import rank_markers, evaluate_panels, known_marker_ranks

ds  = data.build_dataset()                    # Dataset: proteins, X_pre, train/val/test Splits, classes
enc = get_encoder("raw").fit(ds)              # elastic-net baseline; enc.probe_l1_ratio == 0.5
ranking = rank_markers(enc, ds, n_boot=20)    # DataFrame: protein, gene, block, importance, importance_sd, stability_top8
panels  = evaluate_panels(ranking, ds, ks=range(1, 31))   # k, macro_f1, balanced_acc, auroc, c_index, markers
```

Outputs (all JSON unless noted):

| File | Contents |
|---|---|
| `qc.json` | patients per split, subtype counts, survival events, missingness per protein and per pathway block |
| `markers.json` | full ranking with importance ± sd, stability, pathway block, gene; plus known-marker ranks |
| `panels.json` | metrics and marker lists for k = 1..30, plus the full-model reference (all 198 proteins) |
| `latent.json` | 2-D PCA coordinates of train + test patients with subtype and split (TCGA id on test points only) |
| `patients.json` | locked test patients: subtype, PFS, z-scores of the top-30 markers, per-k probabilities and calls |
| `models.json` | the six-model comparison table above, with `"preliminary": true` and run settings |
| `model.joblib` | fitted scaler + elastic-net subtype model on all 198 proteins (for `/api/predict`) |
| `meta.json` | build time, data source URL, protein list, class list, git commit |

Also store the training-set z-score parameters so uploaded data is transformed identically.

## API contract

All responses carry `"research_use_only": true`. Errors use FastAPI's default `{"detail": ...}`.

| Method & path | Returns |
|---|---|
| `GET /api/health` | `{status, artifacts_built_at}` |
| `GET /api/diseases` | `[{id:"brca", name:"Breast cancer", enabled:true}, …others enabled:false}]` |
| `GET /api/dataset/qc?disease=brca` | contents of `qc.json` |
| `GET /api/markers?disease=brca` | ranking rows `{rank, protein, gene, block, importance, importance_sd, stability}` + `known_markers` |
| `GET /api/panel?disease=brca&goal=subtype&k=8` | `{k, markers[], metrics{macro_f1, balanced_acc, auroc, c_index}, full_model{…}, test_n:176, preliminary:true}` |
| `POST /api/panel/custom` `{markers:[protein…]}` | same shape, refit live on the given markers (≤ 30) |
| `GET /api/latent?disease=brca` | `[{x, y, subtype, split}]` |
| `GET /api/models` | contents of `models.json` |
| `GET /api/patients?disease=brca&k=8` | the 176 **locked test** patients: `{id, subtype, predicted, confidence, mismatch, pfs_months, pfs_event}` from the top-k panel |
| `GET /api/patients/{id}?k=8` | one test patient: subtype probabilities + z-scores of the k panel markers (missing flagged) |
| `POST /api/predict` (CSV upload) | per-row subtype probabilities + QC: matched/missing proteins. Research use only. |

`goal=survival` in the MVP: return the same subtype-ranked panel with its C-index highlighted, and say in
the response (`note`) that survival-specific ranking is not built yet. Don't fake a survival ranking.

## Frontend screens

Design language: **warm dark, minimal.** Warm charcoal background (`--bg #13100E`), cards on `--raise` with
rounded corners (`rounded-2xl`), a 1px `--line` border and a soft shadow; warm white text (`--fg #F3EDE5`). Text is
DM Sans; labels, numbers and data are JetBrains Mono (`.tabular-nums` is mono). One accent, the deck yellow
`#EEE772` in dark (deck navy `#2E3F8F` in the light "paper" theme, a `light mode` toggle stored in localStorage),
used for the panel's hero number, the budget, in-panel importance bars and focus. Pills for nav, buttons, toggles and
marker chips. Sections stay numbered `01 02 03`. Colour beyond the accent is reserved for data (subtype tokens
`--c-<Subtype>`: LumA cyan, LumB amber, Basal violet, Her2 green, Normal pink, CVD-separated in both themes; subtype
names are also written on the map; mismatches use a `≠` glyph, not a colour). All colours are CSS tokens in
`frontend/src/index.css`; don't hard-code hex in components. Keep WCAG AA contrast and keyboard navigation everywhere.
Print (export) switches every token to black on white.

1. **Landing:** one-line value prop, the problem in three numbers, CTA "Design a panel", disclaimer.
2. **Designer** (the demo; build this first):
   - Left rail: disease (only breast cancer enabled), goal (subtype / survival), assay type (IHC / qPCR,
     informational for now), **marker budget slider 1–30**.
   - Main: **QC card** (patients, missingness, events) → **2-D map** coloured by subtype →
     **marker list** (rank, protein, pathway chip, importance bar, stability %) →
     **panel card**: macro-F1, balanced accuracy, C-index, comparison to the full 198-protein model,
     "Locked test set · n = 176 · preliminary".
   - Optional **cost per test**: the user enters their lab's cost per marker; multiply by k. Never invent prices.
   - **Export** button: print-styled panel report (markers, metrics, method, disclaimer, date).
   - Moving the slider must update the panel card instantly (precomputed data).
3. **Patients:** the 176 locked test patients only (never training patients): searchable list with PAM50 vs
   panel call (mismatches flagged), confidence and PFS; a detail view with subtype probabilities and each panel
   marker's z-score against the cohort. Shares the marker budget with the Designer; rings on the 2-D map link here.
4. **Evidence & methods** (one page; `/methods` redirects): the six-model chart, bottleneck table, known-driver
   check, validation design, then data source, split, metrics, ranking, limitations, references.

Navigation is three items: designer · patients · evidence. The Designer's controls sit in one bar
(disease, goal, budget slider, export; assay type and cost behind "assay & cost"), with the panel card and
marker list side by side and the map / QC / method as tabs below.

## Honesty rules (non-negotiable)

- Every metric shown names its test set (locked, n = 176) and says **preliminary** until replaced.
- Never show a number the pipeline didn't produce. No mock metrics in the deployed site; use loading
  skeletons, not fake data.
- No clinical language: "candidate panel", "research use only", never "diagnose" or "treatment".
- Don't claim multi-omics fusion in the product UI; the live engine is proteins only. RNA and fusion are on
  the Evidence/Methods pages as "in development".
- Keep the locked test set locked: no tuning, ranking or model selection may touch `ds.test`.

## Commands

```bash
# ML artifacts (needs network the first time to download TCGA files)
cd ml && pip install -r requirements.txt && python build_artifacts.py --out ../artifacts

# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload    # http://localhost:8000/docs

# Frontend
cd frontend && npm install && npm run dev        # proxies /api to :8000

# Tests
cd backend && pytest
cd frontend && npm run test && npm run build

# Container
docker build -t miach . && docker run -p 8000:8000 miach
```

## Testing

- `backend/tests/test_panel.py`: `/api/panel?k=8` returns exactly the k = 8 row of `panels.json`;
  `/api/panel/custom` with those 8 markers reproduces the same macro-F1 within 1e-6.
- Contract test: every endpoint's JSON validates against its Pydantic schema and includes `research_use_only`.
- `/api/predict`: a CSV with missing protein columns returns QC listing them and still predicts.
- Frontend: slider changes k and the panel card updates; no request returns 5xx in a click-through smoke test.
- Before deploying: open the built site, move the slider end to end, export a report, check mobile width.

## Build order (one week)

| Day | Deliverable |
|---|---|
| 1 | `build_artifacts.py`; artifacts committed; numbers match "Ground truth" above |
| 2 | FastAPI with all GET endpoints + tests |
| 3 | Designer page: rail, slider, panel card, marker list (wired to the API) |
| 4 | QC card, 2-D map, export report; Evidence page |
| 5 | Docker image deployed to miach.online; Landing + Methods pages |
| 6 | `/api/predict` upload (stretch), polish, accessibility pass, mobile |
| 7 | Freeze. Rehearse the 3-minute demo; record a backup video |

If time runs short, cut in this order: predict upload → Methods page → cost field → 2-D map. Never cut the
slider + panel card; it is the demo.

## Out of scope this week

Multi-omics fusion in the live product, RNA data, MOFA+, TabPFN in production (licence check first),
user accounts, databases, a chat copilot, survival-specific marker ranking, any clinical claims.
