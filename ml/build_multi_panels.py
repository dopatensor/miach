"""Precompute panels k = 1..30 for lung and colorectal (four-cancer run). Run once; commit the output.

    python build_multi_panels.py --out ../artifacts

Same panel procedure as the breast build (miach_panel.fit_panel): L2 logistic regression on the
top-k proteins of markers_<cancer>.csv, C chosen on a validation split, refit on train + validation,
scored once on the locked test split. The four-cancer run has no separate validation split, so one is
carved from the training patients (stratified, fixed seed). The locked test split comes from
cancers.build_multi and is never used for ranking, C or anything else.

Ovarian has no subtype labels and therefore no panel.
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config as C
from cancers import CANCERS, build_multi
from miach_panel import fit_panel

PANEL_CANCERS = ("lung", "crc")
KS = range(1, 31)
RESULTS = Path(__file__).resolve().parent / "results_multi"
EVENT_WORD = {"PFS": "progression", "OS": "death"}


def _r(v, d=4):
    return None if v is None or v != v else round(float(v), d)


def build(key: str, ds) -> dict:
    sp, meta = ds.splits[key], CANCERS[key]
    classes = sp["classes"]
    tr, te = sp["train"], sp["test"]

    # Validation split carved from training patients (labelled ones), stratified, fixed seed.
    lab = np.array([s is not None for s in tr.subtype])
    idx = np.where(lab)[0]
    tr_idx, va_idx = train_test_split(idx, test_size=C.VAL_FRACTION, random_state=C.SPLIT_SEED,
                                      stratify=tr.subtype[idx].astype(str))

    # Missing values: training-set median of the (pan-cancer z-scored) values; 0 if never measured.
    with warnings.catch_warnings():  # proteins never measured in this cancer -> imputed as 0 below
        warnings.simplefilter("ignore", RuntimeWarning)
        med = np.nanmedian(tr.X[tr_idx], axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    fill = lambda X: np.where(np.isnan(X), med, X)
    y = lambda s: np.array([classes.index(v) if v is not None else -1 for v in s.subtype])
    y_tr = y(tr)

    # Subtype-derived risk for the C-index: training events per 100 person-months, per class.
    ok = (y_tr >= 0) & np.isfinite(tr.time) & np.isfinite(tr.event)
    hazard = [100 * tr.event[ok & (y_tr == c)].sum() / max(tr.time[ok & (y_tr == c)].sum(), 1e-9)
              for c in range(len(classes))]

    arrays = {
        "X_train": fill(tr.X[tr_idx]), "y_train": y_tr[tr_idx],
        "X_val": fill(tr.X[va_idx]), "y_val": y_tr[va_idx],
        "X_test": fill(te.X), "y_test": y(te),
        "t_test": te.time.astype(float), "e_test": np.nan_to_num(te.event, nan=-1.0),
        "subtype_hazard": np.array(hazard),
    }

    ranking = pd.read_csv(RESULTS / f"markers_{key}.csv")
    col = {p: i for i, p in enumerate(ds.proteins)}
    missing = [p for p in ranking["protein"] if p not in col]
    assert not missing, f"{key}: ranked proteins not in dataset: {missing[:5]}"

    panels = []
    for k in KS:
        top = ranking.head(k)
        res = fit_panel(arrays, [col[p] for p in top["protein"]])
        panels.append({"k": k, "markers": [p.split("|")[1] for p in top["protein"]],
                       "metrics": {m: _r(v) for m, v in res["metrics"].items()}})
        print(f"  {key} k={k:2d}  macro-F1 {res['metrics']['macro_f1']:.3f}  C {res['C']}", flush=True)
    full = fit_panel(arrays, list(range(len(ds.proteins))))

    endpoint = meta["survival"]
    csv = pd.read_csv(RESULTS / "multi_metrics.csv")
    enet = csv.query("encoder == 'raw' and cancer == @key and fraction == 1.0").macro_f1.item()
    return {
        "disease": key,
        "goal": "subtype",
        "task": meta["task"],
        "classes": classes,
        "label_name": "subtype label" if key == "crc" else "histology label",
        "survival_endpoint": endpoint,
        "event_word": EVENT_WORD[endpoint],
        "test_n": int(len(te.X)),
        "test_labelled": int((y(te) >= 0).sum()),
        "test_events": int(np.nansum(te.event[np.isfinite(te.time)] == 1)),
        "train_n": int(len(tr_idx)), "val_n": int(len(va_idx)),
        "preliminary": True,
        "panel_model": ("L2 logistic regression on the top-k ranked proteins (four-cancer ranking); C chosen on a "
                        "validation split carved from the training patients, refit on train + validation, scored "
                        "once on the locked test set. The all-proteins reference uses this same procedure; the "
                        f"Results page's elastic net on all proteins (3-fold CV probe) scored {enet:.2f}"),
        "c_index_note": (f"C-index ({endpoint}) of a class-derived risk score (predicted class probabilities x "
                         f"training-set {EVENT_WORD[endpoint]} rate per class); survival-specific ranking is not built yet"),
        "panels": panels,
        "full_model": {"k": len(ds.proteins), "model": "L2 logistic regression (all proteins, same procedure)",
                       "metrics": {m: _r(v) for m, v in full["metrics"].items()}},
        "source": "ml/build_multi_panels.py (cancers.build_multi split, markers_<cancer>.csv ranking)",
    }


def main(out: Path) -> None:
    ds = build_multi()
    for key in PANEL_CANCERS:
        obj = build(key, ds)
        (out / f"panels_{key}.json").write_text(json.dumps(obj, allow_nan=False, indent=1) + "\n")
        print(f"{key}: test n={obj['test_n']} labelled={obj['test_labelled']} events={obj['test_events']}; "
              f"full model macro-F1 {obj['full_model']['metrics']['macro_f1']}")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "artifacts")
    main(a.parse_args().out)
