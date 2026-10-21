"""Build every artifact the website serves. Run once; commit the output.

    python build_artifacts.py --out ../artifacts

Nothing here is tuned on the locked test split: model selection uses the
validation split, ranking uses training out-of-bag + validation patients, and
the test split is only scored.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import PCA

import build_data as data
from encoders.raw import RawElasticNet
from miach_panel import c_index, classification_metrics
from build_panel import evaluate_panels, known_marker_ranks, rank_markers
from build_pathways import block_of, split_id

# Six-model comparison measured by the omics_mvp research pipeline (locked test, n = 176).
# Deep models are not rebuilt here; they are a research track shown on the Evidence page only.
MODEL_TABLE = [
    {"model": "Elastic net (raw proteins)", "kind": "linear", "f1_10": 0.56, "f1_100": 0.63, "production": True},
    {"model": "PCA + probe", "kind": "linear", "f1_10": 0.52, "f1_100": 0.59, "production": False},
    {"model": "VAE + probe", "kind": "deep", "f1_10": 0.49, "f1_100": 0.55, "production": False},
    {"model": "VAE + heads", "kind": "deep", "f1_10": 0.47, "f1_100": 0.56, "production": False},
    {"model": "Reconstruction control", "kind": "deep", "f1_10": 0.32, "f1_100": 0.58, "production": False},
    {"model": "Pathway JEPA", "kind": "deep", "f1_10": 0.39, "f1_100": 0.57, "production": False},
]


def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def _dump(path: Path, obj, compact: bool = False) -> None:
    kw = {"separators": (",", ":")} if compact else {"indent": 1}
    path.write_text(json.dumps(obj, allow_nan=False, **kw) + "\n")


def subtype_hazard(ds) -> list[float]:
    """Training-set progression events per 100 person-months, per PAM50 subtype."""
    tr = ds.train
    ok = tr.labelled & ~np.isnan(tr.pfs_time) & (tr.pfs_event >= 0)
    out = []
    for c in range(len(ds.classes)):
        m = ok & (tr.y == c)
        out.append(100 * tr.pfs_event[m].sum() / max(tr.pfs_time[m].sum(), 1e-9))
    return out


def main(out: Path, n_boot: int) -> None:
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    ds = data.build_dataset()
    splits = {"train": ds.train, "val": ds.val, "test": ds.test}
    print(f"patients: " + ", ".join(f"{k} {len(s.ids)}" for k, s in splits.items()))

    hazard = subtype_hazard(ds)
    arrays = {
        **{f"X_{k}": s.X for k, s in splits.items()},
        **{f"y_{k}": s.y for k, s in splits.items()},
        "t_test": ds.test.pfs_time, "e_test": ds.test.pfs_event,
        "subtype_hazard": np.array(hazard),
    }
    np.savez_compressed(out / "arrays.npz", **arrays)

    # --- QC ---------------------------------------------------------------
    blocks = [block_of(p) for p in ds.proteins]
    miss = ds.missing_raw
    qc = {
        "disease": "brca",
        "n_patients": sum(len(s.ids) for s in splits.values()),
        "n_proteins": len(ds.proteins),
        "splits": {
            k: {
                "patients": len(s.ids),
                "labelled": int(s.labelled.sum()),
                "subtypes": {c: int((s.y == i).sum()) for i, c in enumerate(ds.classes)},
                "unlabelled": int((~s.labelled).sum()),
                "pfs_events": int((s.pfs_event == 1).sum()),
            }
            for k, s in splits.items()
        },
        "missingness": {
            "overall": _r(miss.mean()),
            "proteins_any_missing": int((miss > 0).sum()),
            "proteins_fully_missing": int((miss >= 1).sum()),
            "per_protein": [
                {"protein": split_id(p)[1], "gene": split_id(p)[0], "block": b, "missing": _r(m)}
                for p, b, m in zip(ds.proteins, blocks, miss.to_numpy())
            ],
            "per_block": [
                {"block": b, "proteins": int(sum(x == b for x in blocks)),
                 "missing": _r(np.mean([m for x, m in zip(blocks, miss.to_numpy()) if x == b]))}
                for b in sorted(set(blocks))
            ],
        },
        "imputation": "training-set median, then z-score with training mean/sd",
    }
    _dump(out / "qc.json", qc)

    # --- Production model (elastic net on all proteins) -------------------
    print("fitting elastic net ...")
    enc = RawElasticNet().fit(ds)
    te = ds.test
    proba = enc.predict_proba(te.X[te.labelled])
    full = classification_metrics(te.y[te.labelled], proba, len(ds.classes))
    full["c_index"] = c_index(te.pfs_time, te.pfs_event, enc.predict_proba(te.X) @ np.array(hazard))
    print(f"  full model C={enc.C} test macro-F1 {full['macro_f1']:.3f}")
    joblib.dump({
        "model": enc.model, "proteins": ds.proteins, "classes": ds.classes,
        "median": ds.median, "mean": ds.mean, "std": ds.std,
    }, out / "model.joblib")

    # --- Marker ranking ----------------------------------------------------
    print(f"ranking markers ({n_boot} bootstraps) ...")
    ranking = rank_markers(enc, ds, n_boot=n_boot)
    known = known_marker_ranks(ranking)
    for k in known:
        print(f"  {k['protein']}: #{k['rank']}")
    _dump(out / "markers.json", {
        "disease": "brca",
        "method": "occlusion importance (drop in true-class log-likelihood) of the elastic net, "
                  f"{n_boot} bootstrap refits on training patients, scored on out-of-bag + validation patients",
        "markers": [
            {"rank": int(r["rank"]), "protein": r["protein"], "protein_id": r["protein_id"], "gene": r["gene"],
             "block": r["block"], "importance": _r(r["importance"], 5), "importance_sd": _r(r["importance_sd"], 5),
             "stability": _r(r["stability_top8"], 3)}
            for _, r in ranking.iterrows()
        ],
        "known_markers": known,
    })

    # --- Panels k = 1..30 ------------------------------------------------
    print("evaluating panels k = 1..30 ...")
    panels = evaluate_panels(ranking, arrays, ks=range(1, 31))
    _dump(out / "panels.json", {
        "disease": "brca",
        "goal": "subtype",
        "test_n": len(te.ids),
        "test_labelled": int(te.labelled.sum()),
        "test_events": int((te.pfs_event == 1).sum()),
        "preliminary": True,
        "panel_model": "L2 multinomial logistic regression on the top-k ranked proteins; C chosen on validation, "
                       "refit on train + validation, scored once on the locked test set",
        "c_index_note": "C-index of a subtype-derived risk score (predicted subtype probabilities x training-set "
                        "progression rate per subtype); survival-specific ranking is not built yet",
        "panels": [
            {"k": int(r.k), "markers": r.markers,
             "metrics": {m: _r(getattr(r, m)) for m in ("macro_f1", "balanced_acc", "auroc", "c_index")}}
            for r in panels.itertuples()
        ],
        "full_model": {"k": len(ds.proteins), "model": "Elastic net (all proteins)",
                       "metrics": {m: _r(v) for m, v in full.items()}},
    })
    print(panels[["k", "macro_f1", "balanced_acc", "c_index"]].round(3).to_string(index=False))

    # --- Patients (locked test split only) --------------------------------
    rppa, _ = data.load_raw()
    top30 = ranking.head(30)
    raw_missing = rppa.loc[te.ids].isna().to_numpy()
    patients = []
    for i, pid in enumerate(te.ids):
        patients.append({
            "id": pid,
            "subtype": ds.classes[te.y[i]] if te.y[i] >= 0 else None,
            "pfs_months": _r(te.pfs_time[i], 1),
            "pfs_event": None if te.pfs_event[i] < 0 else int(te.pfs_event[i]),
            "z": [_r(te.X[i, c], 3) for c in top30["col"]],
            "missing": [p for p, c in zip(top30["protein"], top30["col"]) if raw_missing[i, c]],
        })
    _dump(out / "patients.json", {
        "split": "test",
        "classes": ds.classes,
        "markers": top30["protein"].tolist(),
        "patients": patients,
        # predictions[k-1][i] = subtype probabilities of patient i from the top-k panel model
        "predictions": [[[_r(v, 3) for v in row] for row in r.test_proba] for r in panels.itertuples()],
        # calls[k-1][i] = predicted class index, taken before rounding so ties cannot flip it
        "calls": [[int(row.argmax()) for row in r.test_proba] for r in panels.itertuples()],
        "note": "Locked test patients only. Values are training-set z-scores; missing values were imputed "
                "with the training median.",
    }, compact=True)

    # --- 2-D map ----------------------------------------------------------
    pca = PCA(n_components=2, random_state=0).fit(ds.train.X)
    pts = []
    for name in ("train", "test"):
        s = splits[name]
        xy = pca.transform(s.X)
        for (x, y), lab, pid in zip(xy, s.y, s.ids):
            pts.append({"x": _r(x, 3), "y": _r(y, 3),
                        "subtype": ds.classes[lab] if lab >= 0 else "Unknown", "split": name,
                        "id": pid if name == "test" else None})
    _dump(out / "latent.json", {
        "method": "PCA fitted on training patients (z-scored proteins)",
        "explained_variance": [_r(v) for v in pca.explained_variance_ratio_],
        "points": pts,
    })

    # --- Model comparison -------------------------------------------------
    _dump(out / "models.json", {
        "preliminary": True,
        "metric": "subtype macro-F1, locked test set (n = 176)",
        "settings": {"labels": ["10%", "100%"], "seed": 0, "split": "595 train / 105 val / 176 test (patient level)",
                     "pretraining_pool": "7,084 tumours, 31 TCGA cancer types (deep models only)"},
        "source": "omics_mvp research comparison (run_compare.py)",
        "models": MODEL_TABLE,
        "rebuild_check": {"model": "Elastic net (raw proteins), this build, 100% labels",
                          "macro_f1": _r(full["macro_f1"])},
    })

    # --- Meta -------------------------------------------------------------
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = None
    _dump(out / "meta.json", {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": ds.source_url,
        "git_commit": commit,
        "proteins": [split_id(p)[1] for p in ds.proteins],
        "protein_ids": ds.proteins,
        "classes": ds.classes,
        "zscore": {"median": [_r(v, 6) for v in ds.median], "mean": [_r(v, 6) for v in ds.mean],
                   "std": [_r(v, 6) for v in ds.std]},
        "elastic_net": {"C": enc.C, "l1_ratio": enc.probe_l1_ratio, "val_macro_f1": _r(enc.val_macro_f1)},
        "build_seconds": round(time.time() - t0, 1),
    })
    print(f"done in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "artifacts")
    ap.add_argument("--n-boot", type=int, default=20)
    a = ap.parse_args()
    main(a.out, a.n_boot)
