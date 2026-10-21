"""Evaluate encoders on four cancers with one shared pretraining.

    python run_multi.py --encoders raw,pca,vae,jepa,recon --epochs 5
"""
from __future__ import annotations

import argparse
import json
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd

import config as C
import evaluate as E
from cancers import CANCERS, build_multi, describe
from encoders import LABELS, get_encoder
from panel import known_marker_ranks, rank_markers

KNOWN = {"brca": ["ESR1", "PGR", "ERBB2", "GATA3"], "lung": ["NKX2-1", "TP63", "KRT5"],
         "crc": ["MSH2", "MSH6", "MLH1"], "ov": []}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--encoders", default="raw,pca,vae,jepa,recon")
    a.add_argument("--epochs", type=int, default=5)
    a.add_argument("--seeds", type=int, default=3)
    a.add_argument("--fractions", default="0.1,1.0")
    a.add_argument("--n-boot", type=int, default=500)
    a.add_argument("--marker-boot", type=int, default=5)
    a.add_argument("--out", default="results_multi")
    args = a.parse_args()
    out = C.RESULTS_DIR.parent / args.out
    out.mkdir(parents=True, exist_ok=True)

    ds = build_multi()
    print(describe(ds), "\n", flush=True)
    fracs = [float(f) for f in args.fractions.split(",")]
    rows, health, times = [], {}, {}

    for name in args.encoders.split(","):
        cfg = {"epochs": args.epochs} if name in ("jepa", "recon") else {}
        t0 = time.time()
        enc = get_encoder(name, **cfg).fit(ds, seed=0)
        times[name] = time.time() - t0
        print(f"=== {LABELS[name]} fitted in {times[name]:.0f}s", flush=True)
        for key, sp in ds.splits.items():
            tr, te = sp["train"], sp["test"]
            Ztr, Zte = enc.embed(tr.X), enc.embed(te.X)
            if key == "brca":
                health[name] = E.collapse_stats(Zte)
            # survival on all training patients
            ok_tr = np.isfinite(tr.time) & np.isfinite(tr.event)
            ok_te = np.isfinite(te.time) & np.isfinite(te.event)
            cox = E.CoxProbe().fit(Ztr[ok_tr], tr.time[ok_tr], tr.event[ok_tr])
            risk = cox.risk(Zte[ok_te])
            ci = E.c_index(te.time[ok_te], te.event[ok_te], risk)
            ci_lo, ci_hi = E.bootstrap_ci(E.cindex_from_output,
                                          [{"time": te.time[ok_te], "event": te.event[ok_te], "risk": risk}],
                                          int(ok_te.sum()), args.n_boot)
            base = {"encoder": name, "cancer": key, "c_index": ci, "c_lo": ci_lo, "c_hi": ci_hi}
            if not sp["classes"]:
                rows.append({**base, "fraction": 1.0, "macro_f1": np.nan, "f1_lo": np.nan, "f1_hi": np.nan,
                             "balanced_acc": np.nan, "auroc": np.nan})
                print(f"  {key}: C-index {ci:.3f}", flush=True)
                continue
            lab_te = np.array([s is not None for s in te.subtype])
            y_te = te.subtype[lab_te].astype(str)
            for frac in fracs:
                outs, ms = [], []
                for s in range(args.seeds):
                    idx = E.subsample_labelled(tr.subtype, frac, seed=1000 * s + int(frac * 100))
                    pr = E.SubtypeProbe(l1_ratio=enc.probe_l1_ratio, seed=s).fit(Ztr[idx], tr.subtype[idx].astype(str))
                    proba = pr.predict_proba(Zte[lab_te])
                    ms.append(E.subtype_metrics(y_te, proba, pr.classes_))
                    outs.append({"y": y_te, "proba": proba, "classes": pr.classes_})
                lo, hi = E.bootstrap_ci(E.f1_from_output, outs, len(y_te), args.n_boot)
                m = pd.DataFrame(ms).mean()
                rows.append({**base, "fraction": frac, "macro_f1": m.macro_f1, "f1_lo": lo, "f1_hi": hi,
                             "balanced_acc": m.balanced_acc, "auroc": m.auroc})
                print(f"  {key} {frac:.0%}: macro-F1 {m.macro_f1:.3f} [{lo:.3f},{hi:.3f}]  "
                      f"bal-acc {m.balanced_acc:.3f}  C-index {ci:.3f}", flush=True)

        if name == "raw":
            for key, sp in ds.splits.items():
                if not sp["classes"]:
                    continue
                shim = SimpleNamespace(train=sp["train"], proteins=ds.proteins)
                rk = rank_markers(enc, shim, n_boot=args.marker_boot)
                rk.to_csv(out / f"markers_{key}.csv")
                hits = {}
                for g in KNOWN[key]:
                    h = rk.index[rk["gene"].str.split().apply(lambda gs: g in gs)]
                    hits[g] = int(h.min()) if len(h) else None
                (out / f"known_{key}.json").write_text(json.dumps(
                    {"known": hits, "top10": rk["protein"].head(10).str.split("|").str[1].tolist()}, indent=1))
                print(f"  markers {key}: top5 {rk['protein'].head(5).str.split('|').str[1].tolist()} known {hits}", flush=True)

        df = pd.DataFrame(rows)
        df.to_csv(out / "multi_metrics.csv", index=False)
    (out / "health.json").write_text(json.dumps({"health": health, "fit_seconds": times}, indent=1, default=float))
    print("done", flush=True)


if __name__ == "__main__":
    main()
