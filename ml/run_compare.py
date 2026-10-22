"""Train every encoder, probe it at several label budgets, and write a comparison report.

    python run_compare.py --quick                 # ~minutes, smoke test on a few cancer types
    python run_compare.py                         # full run
    python run_compare.py --encoders raw,pca      # no PyTorch needed
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

import config as C
import data
import evaluate as E
from encoders import ALL, LABELS, get_encoder
from panel import evaluate_panels, known_marker_ranks, rank_markers

QUICK_STUDIES = ["brca", "ov", "ucec", "luad", "lusc", "coadread", "skcm", "kirc"]


def parse():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--encoders", default=",".join(ALL))
    a.add_argument("--fractions", default=",".join(str(f) for f in C.LABEL_FRACTIONS))
    a.add_argument("--seeds", type=int, default=len(C.PROBE_SEEDS), help="label-subsample/probe seeds")
    a.add_argument("--encoder-seeds", type=int, default=1,
                   help="independently pretrained copies of each unsupervised encoder (3 recommended for the final run)")
    a.add_argument("--epochs", type=int, default=None, help="transformer (JEPA/recon) epochs")
    a.add_argument("--vae-epochs", type=int, default=None)
    a.add_argument("--panel", default="raw,vae_joint,jepa", help="encoders to rank markers for ('' to skip)")
    a.add_argument("--panel-boot", type=int, default=10)
    a.add_argument("--n-boot", type=int, default=C.N_BOOTSTRAP)
    a.add_argument("--threads", type=int, default=None)
    a.add_argument("--tf-opt", action="append", default=[], metavar="KEY=VALUE",
                   help="override a transformer (jepa/recon) setting, e.g. --tf-opt target_norm=batch "
                        "--tf-opt n_mask_blocks=4 --tf-opt d=64. Repeatable.")
    a.add_argument("--quick", action="store_true", help="few cancer types, few epochs, 2 seeds")
    a.add_argument("--out", default=str(C.RESULTS_DIR))
    return a.parse_args()


def encoder_cfg(name, args):
    cfg = {"threads": args.threads} if name not in ("raw", "pca") else {}
    if name in ("jepa", "recon"):
        if args.epochs:
            cfg["epochs"] = args.epochs
        elif args.quick:
            cfg["epochs"] = 3
        for kv in args.tf_opt:
            k, v = kv.split("=", 1)
            try:
                cfg[k] = json.loads(v)       # numbers, true/false
            except json.JSONDecodeError:
                cfg[k] = v                   # plain strings like batch, token, cuda
    if name in ("vae", "vae_joint"):
        if args.vae_epochs:
            cfg["epochs"] = args.vae_epochs
        elif args.quick:
            cfg.update(epochs=10, ft_epochs=60)
    return cfg


def main():
    args = parse()
    if args.quick:
        args.seeds, args.n_boot, args.panel_boot = min(args.seeds, 2), min(args.n_boot, 200), min(args.panel_boot, 2)
    out = C.RESULTS_DIR.__class__(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = [n for n in args.encoders.split(",") if n]
    fractions = [float(f) for f in args.fractions.split(",")]
    seeds = list(range(args.seeds))

    ds = data.build_dataset(QUICK_STUDIES if args.quick else None)
    print(data.describe(ds), "\n")

    te = ds.test
    lab_te = np.array([s is not None for s in te.subtype])
    sv_te = np.isfinite(te.time) & np.isfinite(te.event)
    y_te = te.subtype[lab_te].astype(str)
    sv_tr_all = np.isfinite(ds.train.time) & np.isfinite(ds.train.event)

    rows, outputs, health, fit_times, logs, fitted = [], {}, {}, {}, {}, {}

    for name in names:
        print(f"=== {LABELS[name]} ===", flush=True)
        cfg = encoder_cfg(name, args)
        proto = get_encoder(name, **cfg)
        unsup_models = []
        if not proto.supervised:
            for es in range(args.encoder_seeds):
                t0 = time.time()
                enc = get_encoder(name, **cfg).fit(ds, seed=es)
                fit_times.setdefault(name, []).append(time.time() - t0)
                unsup_models.append(enc)
                logs[f"{name}_seed{es}"] = enc.log
            Zte0 = unsup_models[0].embed(te.X)
            health[name] = E.collapse_stats(Zte0)
            fitted[name] = unsup_models[0]
        sup_enc = proto if proto.supervised else None

        for frac in fractions:
            for s in seeds:
                idx = E.subsample_labelled(ds.train.subtype, frac, seed=1000 * s + int(frac * 100))
                if sup_enc is not None:
                    t0 = time.time()
                    enc = sup_enc.fit(ds, labelled_idx=idx, seed=s)
                    fit_times.setdefault(name, []).append(time.time() - t0)
                    if frac == 1.0 and s == 0:
                        health[name] = E.collapse_stats(enc.embed(te.X))
                        import copy
                        fitted[name] = copy.deepcopy(enc)
                else:
                    enc = unsup_models[s % len(unsup_models)]
                Ztr, Zte = enc.embed(ds.train.X), enc.embed(te.X)

                probe = E.SubtypeProbe(l1_ratio=enc.probe_l1_ratio, seed=s).fit(
                    Ztr[idx], ds.train.subtype[idx].astype(str))
                proba = probe.predict_proba(Zte[lab_te])
                m = E.subtype_metrics(y_te, proba, probe.classes_)

                sv_idx = idx[sv_tr_all[idx]]
                cox = E.CoxProbe(seed=s).fit(Ztr[sv_idx], ds.train.time[sv_idx], ds.train.event[sv_idx])
                risk = cox.risk(Zte[sv_te])
                ci = E.c_index(te.time[sv_te], te.event[sv_te], risk)

                outputs.setdefault((name, frac), []).append({
                    "y": y_te, "proba": proba, "classes": probe.classes_,
                    "time": te.time[sv_te], "event": te.event[sv_te], "risk": risk})
                rows.append({"encoder": name, "fraction": frac, "seed": s, "n_labelled": len(idx),
                             "n_events_train": int(ds.train.event[sv_idx].sum()), **m, "c_index": ci})
                print(f"  frac {frac:.2f} seed {s}: macro-F1 {m['macro_f1']:.3f}  "
                      f"bal-acc {m['balanced_acc']:.3f}  C-index {ci:.3f}", flush=True)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(out / "metrics.csv", index=False)

    # ------------------------------------------------------------- summary with CIs
    summ = []
    for (name, frac), outs in outputs.items():
        f1_lo, f1_hi = E.bootstrap_ci(E.f1_from_output, outs, len(y_te), args.n_boot)
        ci_lo, ci_hi = E.bootstrap_ci(E.cindex_from_output, outs, int(sv_te.sum()), args.n_boot)
        sub = metrics[(metrics.encoder == name) & (metrics.fraction == frac)]
        summ.append({"encoder": name, "fraction": frac,
                     "macro_f1": sub.macro_f1.mean(), "macro_f1_sd": sub.macro_f1.std(),
                     "macro_f1_lo": f1_lo, "macro_f1_hi": f1_hi,
                     "balanced_acc": sub.balanced_acc.mean(), "auroc": sub.auroc.mean(),
                     "c_index": sub.c_index.mean(), "c_index_lo": ci_lo, "c_index_hi": ci_hi})
    summary = pd.DataFrame(summ)
    summary.to_csv(out / "summary.csv", index=False)

    # ------------------------------------------------------------- go / no-go
    verdict_lines = []
    low = min(fractions)
    if "jepa" in names:
        comps = {}
        for other in [n for n in ("pca", "recon", "raw", "vae", "vae_joint") if n in names]:
            for frac in fractions:
                comps[(other, frac)] = E.paired_bootstrap_diff(
                    E.f1_from_output, outputs[("jepa", frac)], outputs[(other, frac)],
                    len(y_te), args.n_boot)
        must = [n for n in ("pca", "recon") if n in names]
        collapsed = health.get("jepa", {}).get("collapsed", False)
        wins = [comps[(n, low)] for n in must]
        if collapsed:
            verdict = "NO-GO: the JEPA embeddings collapsed."
        elif must and all(w["lo"] > 0 for w in wins):
            verdict = f"GO: JEPA beats {' and '.join(must)} at {low:.0%} labels, CI excludes zero."
        elif must and all(w["diff"] > 0 for w in wins):
            verdict = (f"LEAN GO: JEPA is ahead of {' and '.join(must)} at {low:.0%} labels, "
                       "but the confidence interval includes zero. Rerun with --encoder-seeds 3.")
        else:
            verdict = f"NO-GO: JEPA does not beat {' and '.join(must) or 'the controls'} at {low:.0%} labels."
        verdict_lines += [f"**{verdict}**", "",
                          "| JEPA minus | Labels | Δ macro-F1 | 95% CI | JEPA wins in |",
                          "|---|---|---|---|---|"]
        for (other, frac), r in comps.items():
            verdict_lines.append(f"| {LABELS[other]} | {frac:.0%} | {r['diff']:+.3f} | "
                                 f"[{r['lo']:+.3f}, {r['hi']:+.3f}] | {r['p_a_wins']:.0%} of resamples |")

    # ------------------------------------------------------------- marker panels
    panel_lines = []
    for name in [n for n in args.panel.split(",") if n in fitted]:
        print(f"=== Marker ranking: {LABELS[name]} ===", flush=True)
        ranking = rank_markers(fitted[name], ds, n_boot=args.panel_boot)
        ranking.to_csv(out / f"markers_{name}.csv")
        panels = evaluate_panels(ranking, ds)
        panels.to_csv(out / f"panel_{name}.csv", index=False)
        known = known_marker_ranks(ranking)
        panel_lines += [f"### {LABELS[name]}", "",
                        "Known-marker rank (of 198 proteins): " +
                        ", ".join(f"{g} #{r}" for g, r in known.items() if r is not None), "",
                        "| Panel size | Macro-F1 | Bal. acc | C-index | Markers |", "|---|---|---|---|---|"]
        for _, r in panels.iterrows():
            panel_lines.append(f"| {r.k} | {r.macro_f1:.3f} | {r.balanced_acc:.3f} | "
                               f"{r.c_index:.3f} | {r.markers} |")
        panel_lines.append("")

    # ------------------------------------------------------------- report
    L = ["# Encoder comparison: TCGA breast cancer, proteins only", "",
         f"Run: {time.strftime('%Y-%m-%d %H:%M')}  ·  quick={args.quick}  ·  probe seeds={len(seeds)}  ·  "
         f"encoder seeds={args.encoder_seeds}  ·  bootstrap={args.n_boot}", "",
         "```", data.describe(ds), "```", "",
         "## Go / no-go", ""] + (verdict_lines or ["JEPA not run."]) + ["",
         "## Subtype (macro-F1, mean over seeds, 95% bootstrap CI) and survival (C-index)", "",
         "| Encoder | Labels | Macro-F1 | 95% CI | Bal. acc | AUROC | C-index | 95% CI |",
         "|---|---|---|---|---|---|---|---|"]
    for _, r in summary.sort_values(["fraction", "encoder"]).iterrows():
        L.append(f"| {LABELS[r.encoder]} | {r.fraction:.0%} | {r.macro_f1:.3f} | "
                 f"[{r.macro_f1_lo:.3f}, {r.macro_f1_hi:.3f}] | {r.balanced_acc:.3f} | {r.auroc:.3f} | "
                 f"{r.c_index:.3f} | [{r.c_index_lo:.3f}, {r.c_index_hi:.3f}] |")
    L += ["", f"Test set: {int(sv_te.sum())} patients with survival, {int(te.event[sv_te].sum())} events; "
          "C-index intervals are wide, so treat survival as a secondary signal.", "",
          "## Representation health (test embeddings)", "",
          "| Encoder | Dim | Rel. spread | Effective rank | Collapsed | Fit time (s) |", "|---|---|---|---|---|---|"]
    for n in names:
        h = health.get(n, {})
        ft = np.mean(fit_times.get(n, [0]))
        L.append(f"| {LABELS[n]} | {h.get('dim', '')} | {h.get('rel_std', float('nan')):.3f} | "
                 f"{h.get('eff_rank', float('nan')):.1f} | {h.get('collapsed', '')} | {ft:.0f} |")
    if panel_lines:
        L += ["", "## Marker panels (top-k raw proteins refit on train, scored on test)", ""] + panel_lines
    (out / "summary.md").write_text("\n".join(L))
    (out / "training_logs.json").write_text(json.dumps(logs, indent=1, default=float))
    (out / "run_config.json").write_text(json.dumps(vars(args), indent=1))
    print("\n" + "\n".join(L))
    print(f"\nFull report: {out / 'summary.md'}")


if __name__ == "__main__":
    main()
