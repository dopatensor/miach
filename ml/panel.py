"""Encoder-agnostic marker ranking and small-panel refit.

Importance = how much worse the subtype prediction gets when one protein is treated as
unmeasured (occlusion). Computed on out-of-bag patients over bootstrap resamples of the
training set only, so the test set never influences which markers are chosen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

import config as C
from evaluate import CoxProbe, SubtypeProbe, c_index, fill, subtype_metrics
from pathways import assign_blocks, gene_symbols


def rank_markers(encoder, ds, n_boot: int = 10, top_k: int = 8, seed: int = 0) -> pd.DataFrame:
    tr = ds.train
    lab = np.array([i for i, s in enumerate(tr.subtype) if s is not None])
    X, y = tr.X[lab], np.array([tr.subtype[i] for i in lab], dtype=object)
    P = X.shape[1]
    rng = np.random.default_rng(seed)
    drops = np.full((n_boot, P), np.nan)

    for b in range(n_boot):
        bi = rng.integers(0, len(lab), len(lab))
        oob = np.setdiff1d(np.arange(len(lab)), bi)
        if len(set(y[bi])) < len(set(y)) or len(oob) < 20:
            continue
        probe = SubtypeProbe(l1_ratio=encoder.probe_l1_ratio, seed=b).fit(encoder.embed(X[bi]), y[bi])
        Xo, yo = X[oob], y[oob]
        base = log_loss(yo, probe.predict_proba(encoder.embed(Xo)), labels=probe.classes_)
        stack = np.repeat(Xo[None], P, axis=0)              # (P, n_oob, P)
        stack[np.arange(P), :, np.arange(P)] = np.nan       # copy p hides protein p
        Z = encoder.embed(stack.reshape(-1, P)).reshape(P, len(oob), -1)
        for p in range(P):
            drops[b, p] = log_loss(yo, probe.predict_proba(Z[p]), labels=probe.classes_) - base
        print(f"    marker bootstrap {b + 1}/{n_boot}", flush=True)

    ok = ~np.isnan(drops).any(1)
    drops = drops[ok]
    ranks = (-drops).argsort(1).argsort(1)                    # 0 = most important in that bootstrap
    block_ids, block_names = assign_blocks(ds.proteins)
    df = pd.DataFrame({
        "protein": ds.proteins,
        "gene": [" ".join(gene_symbols(p)) for p in ds.proteins],
        "block": [block_names[i] for i in block_ids],
        "importance": drops.mean(0),
        "importance_sd": drops.std(0),
        f"stability_top{top_k}": (ranks < top_k).mean(0),
    }).sort_values("importance", ascending=False).reset_index(drop=True)
    df.index += 1
    df.index.name = "rank"
    df.attrs["n_boot"] = int(ok.sum())
    return df


def known_marker_ranks(ranking: pd.DataFrame) -> dict:
    out = {}
    for g in C.KNOWN_MARKERS:
        hits = ranking.index[ranking["gene"].str.split().apply(lambda gs: g in gs)]
        out[g] = int(hits.min()) if len(hits) else None
    return out


def evaluate_panels(ranking: pd.DataFrame, ds, ks=(4, 8, 12, 16, 24), seed: int = 0) -> pd.DataFrame:
    """Refit simple models on only the top-k raw proteins: what a cheap assay would measure."""
    col = {p: i for i, p in enumerate(ds.proteins)}
    tr, te = ds.train, ds.test
    lab_tr = np.array([s is not None for s in tr.subtype])
    lab_te = np.array([s is not None for s in te.subtype])
    sv_tr = np.isfinite(tr.time) & np.isfinite(tr.event)
    sv_te = np.isfinite(te.time) & np.isfinite(te.event)
    rows = []
    for k in ks:
        idx = [col[p] for p in ranking["protein"].iloc[:k]]
        Xtr, Xte = fill(tr.X[:, idx]), fill(te.X[:, idx])
        probe = SubtypeProbe(seed=seed).fit(Xtr[lab_tr], tr.subtype[lab_tr].astype(str))
        m = subtype_metrics(te.subtype[lab_te].astype(str), probe.predict_proba(Xte[lab_te]), probe.classes_)
        cox = CoxProbe(seed=seed).fit(Xtr[sv_tr], tr.time[sv_tr], tr.event[sv_tr])
        ci = c_index(te.time[sv_te], te.event[sv_te], cox.risk(Xte[sv_te]))
        rows.append({"k": k, "macro_f1": m["macro_f1"], "balanced_acc": m["balanced_acc"],
                     "auroc": m["auroc"], "c_index": ci,
                     "markers": ", ".join(ranking["protein"].iloc[:k].str.split("|").str[1])})
    return pd.DataFrame(rows)
