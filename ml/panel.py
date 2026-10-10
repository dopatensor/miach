"""Marker ranking and panel evaluation.

Ranking never looks at the locked test split: each bootstrap refits the elastic
net on a resample of the training patients and measures occlusion importance on
the out-of-bag training patients plus the validation patients.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from encoders.raw import make_probe
from miach_panel import fit_panel
from pathways import block_of, split_id

KNOWN_MARKERS = {
    "ER-alpha": "Defines luminal subtypes (oestrogen receptor).",
    "PR": "Progesterone receptor; luminal marker, correlated with ER-alpha.",
    "HER2": "Defines the HER2-enriched subtype (ERBB2 amplification).",
    "GATA3": "Luminal lineage transcription factor.",
    "Cyclin_B1": "Proliferation; separates LumB and Basal from LumA.",
    "AR": "Androgen receptor; luminal / apocrine signal.",
}


def _occlusion(model, X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Drop in mean log-probability of the true class when each protein is set to its training mean (0)."""
    base = np.log(model.predict_proba(X)[np.arange(len(y)), y] + 1e-12).mean()
    out = np.empty(X.shape[1])
    for j in range(X.shape[1]):
        Xo = X.copy()
        Xo[:, j] = 0.0
        out[j] = base - np.log(model.predict_proba(Xo)[np.arange(len(y)), y] + 1e-12).mean()
    return out


def rank_markers(enc, ds, n_boot: int = 20, seed: int = 0, top: int = 8) -> pd.DataFrame:
    tr, va = ds.train, ds.val
    Xtr, ytr = tr.X[tr.labelled], tr.y[tr.labelled]
    Xva, yva = va.X[va.labelled], va.y[va.labelled]
    rng = np.random.default_rng(seed)
    imps = []
    for b in range(n_boot):
        idx = rng.integers(0, len(ytr), len(ytr))
        oob = np.setdiff1d(np.arange(len(ytr)), idx)
        model = make_probe(enc.C, enc.probe_l1_ratio).fit(Xtr[idx], ytr[idx])
        Xe = np.vstack([Xtr[oob], Xva])
        ye = np.concatenate([ytr[oob], yva])
        imps.append(_occlusion(model, Xe, ye))
        print(f"  bootstrap {b + 1}/{n_boot}", end="\r")
    print()
    imps = np.array(imps)
    ranks = (-imps).argsort(axis=1).argsort(axis=1)
    df = pd.DataFrame({
        "protein": [split_id(p)[1] for p in ds.proteins],
        "protein_id": ds.proteins,
        "gene": [split_id(p)[0] for p in ds.proteins],
        "block": [block_of(p) for p in ds.proteins],
        "col": np.arange(len(ds.proteins)),
        "importance": imps.mean(axis=0),
        "importance_sd": imps.std(axis=0, ddof=1),
        "stability_top8": (ranks < top).mean(axis=0),
    })
    df = df.sort_values(["importance", "stability_top8"], ascending=False).reset_index(drop=True)
    df.insert(0, "rank", np.arange(1, len(df) + 1))
    return df


def evaluate_panels(ranking: pd.DataFrame, arrays: dict, ks=range(1, 31)) -> pd.DataFrame:
    rows = []
    for k in ks:
        top = ranking.head(k)
        res = fit_panel(arrays, top["col"].tolist())
        rows.append({"k": k, **res["metrics"], "C": res["C"], "markers": top["protein"].tolist()})
    return pd.DataFrame(rows)


def known_marker_ranks(ranking: pd.DataFrame) -> list[dict]:
    by_name = ranking.set_index("protein")
    return [
        {"protein": p, "gene": by_name.loc[p, "gene"], "rank": int(by_name.loc[p, "rank"]),
         "of": len(ranking), "role": role}
        for p, role in KNOWN_MARKERS.items() if p in by_name.index
    ]
