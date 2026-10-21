"""Encoder-agnostic evaluation: frozen-embedding probes, metrics, bootstrap CIs,
collapse diagnostics. Nothing here knows which encoder produced the embeddings.
"""
from __future__ import annotations

import warnings

import numpy as np
import sklearn
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

_NEW_SKLEARN = tuple(int(x) for x in sklearn.__version__.split(".")[:2]) >= (1, 8)


# ----------------------------------------------------------------- helpers
def fill(X: np.ndarray) -> np.ndarray:
    """Missing -> 0, i.e. the pretraining-pool mean after z-scoring."""
    return np.nan_to_num(X, nan=0.0)


def make_logreg(C: float, l1_ratio: float = 0.0) -> LogisticRegression:
    kw = dict(C=C, class_weight="balanced", max_iter=5000)
    if l1_ratio > 0:
        kw["solver"] = "saga"
        if _NEW_SKLEARN:
            return LogisticRegression(l1_ratio=l1_ratio, **kw)
        return LogisticRegression(penalty="elasticnet", l1_ratio=l1_ratio, **kw)
    return LogisticRegression(**kw)


# ----------------------------------------------------------------- label subsampling
def subsample_labelled(subtypes: np.ndarray, fraction: float, seed: int,
                       min_per_class: int = 2) -> np.ndarray:
    """Indices of a stratified subset of labelled patients, at least `min_per_class` each."""
    rng = np.random.default_rng(seed)
    labelled = np.array([i for i, s in enumerate(subtypes) if s is not None])
    if fraction >= 1.0:
        return labelled
    chosen = []
    for c in sorted({subtypes[i] for i in labelled}):
        members = labelled[[subtypes[i] == c for i in labelled]]
        n = max(min_per_class, int(round(fraction * len(members))))
        chosen.extend(rng.choice(members, size=min(n, len(members)), replace=False))
    return np.sort(np.array(chosen))


# ----------------------------------------------------------------- subtype probe
class SubtypeProbe:
    """Standardise embeddings, pick C by 3-fold CV (macro-F1), fit balanced logistic regression."""

    def __init__(self, l1_ratio: float = 0.0, Cs=(0.01, 0.1, 1.0, 10.0), seed: int = 0):
        self.l1_ratio, self.Cs, self.seed = l1_ratio, Cs, seed

    def fit(self, Z, y):
        self.scaler = StandardScaler().fit(Z)
        Zs = self.scaler.transform(Z)
        y = np.asarray(y)
        _, counts = np.unique(y, return_counts=True)
        C = 1.0
        if counts.min() >= 3:
            cv = StratifiedKFold(3, shuffle=True, random_state=self.seed)
            scores = []
            for c in self.Cs:
                f = []
                for tr, va in cv.split(Zs, y):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        m = make_logreg(c, self.l1_ratio).fit(Zs[tr], y[tr])
                    f.append(f1_score(y[va], m.predict(Zs[va]), average="macro"))
                scores.append(np.mean(f))
            C = self.Cs[int(np.argmax(scores))]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = make_logreg(C, self.l1_ratio).fit(Zs, y)
        self.C = C
        return self

    def predict_proba(self, Z):
        return self.model.predict_proba(self.scaler.transform(Z))

    @property
    def classes_(self):
        return self.model.classes_


def subtype_metrics(y_true, proba, classes) -> dict:
    y_true = np.asarray(y_true)
    pred = np.asarray(classes)[proba.argmax(1)]
    out = {"macro_f1": f1_score(y_true, pred, average="macro"),
           "balanced_acc": balanced_accuracy_score(y_true, pred)}
    try:
        out["auroc"] = roc_auc_score(y_true, proba, multi_class="ovr", average="macro",
                                     labels=list(classes))
    except ValueError:
        out["auroc"] = np.nan
    return out


# ----------------------------------------------------------------- survival probe
def _cox_nll(beta, Z, event, order, tie_last, alpha):
    r = Z @ beta
    r_sorted = r[order]
    m = r_sorted.max()
    w = np.exp(r_sorted - m)
    S0 = np.cumsum(w)[tie_last]
    S1 = np.cumsum(w[:, None] * Z[order], axis=0)[tie_last]
    e = event[order].astype(bool)
    nll = -(r_sorted[e] - (np.log(S0[e]) + m)).sum() + 0.5 * alpha * beta @ beta
    grad = -(Z[order][e] - S1[e] / S0[e][:, None]).sum(0) + alpha * beta
    n_ev = max(e.sum(), 1)
    return nll / n_ev, grad / n_ev


class CoxProbe:
    """Ridge-penalised Cox regression (Breslow ties) on standardised embeddings."""

    def __init__(self, alphas=(0.1, 1.0, 10.0), seed: int = 0):
        self.alphas, self.seed = alphas, seed

    @staticmethod
    def _fit(Z, t, e, alpha):
        order = np.argsort(-t, kind="stable")
        ts = t[order]
        # risk set {j: t_j >= t_i}: with descending sort, extend each tie group to its last member
        tie_last = np.searchsorted(-ts, -ts, side="right") - 1
        res = minimize(_cox_nll, np.zeros(Z.shape[1]), jac=True, method="L-BFGS-B",
                       args=(Z, e, order, tie_last, alpha))
        return res.x

    def fit(self, Z, t, e):
        self.scaler = StandardScaler().fit(Z)
        Zs = self.scaler.transform(Z)
        alpha = self.alphas[len(self.alphas) // 2]
        if e.sum() >= 15:  # enough events to choose the penalty by CV
            rng = np.random.default_rng(self.seed)
            folds = rng.integers(0, 3, len(t))
            scores = []
            for a in self.alphas:
                cs = []
                for k in range(3):
                    tr, va = folds != k, folds == k
                    if e[va].sum() < 2:
                        continue
                    b = self._fit(Zs[tr], t[tr], e[tr], a)
                    cs.append(c_index(t[va], e[va], Zs[va] @ b))
                scores.append(np.mean(cs) if cs else 0.5)
            alpha = self.alphas[int(np.argmax(scores))]
        self.beta = self._fit(Zs, t, e, alpha)
        self.alpha = alpha
        return self

    def risk(self, Z):
        return self.scaler.transform(Z) @ self.beta


def c_index(time, event, risk) -> float:
    """Harrell's concordance: higher risk should mean earlier event."""
    time, event, risk = map(np.asarray, (time, event, risk))
    comparable = (time[:, None] < time[None, :]) & (event[:, None] == 1)
    if not comparable.any():
        return np.nan
    diff = risk[:, None] - risk[None, :]
    conc = (diff > 0) + 0.5 * (diff == 0)
    return float(conc[comparable].sum() / comparable.sum())


# ----------------------------------------------------------------- representation health
def collapse_stats(Z: np.ndarray) -> dict:
    """Low std or low effective rank means the encoder maps everyone to similar points."""
    Zc = Z - Z.mean(0)
    s = np.linalg.svd(Zc, compute_uv=False)
    p = s / s.sum() if s.sum() > 0 else np.ones_like(s) / len(s)
    eff_rank = float(np.exp(-(p * np.log(p + 1e-12)).sum()))
    # Scale-free spread: near 0 when everyone maps to (nearly) the same point. Effective rank
    # alone misses this, because tiny noise around a constant still looks high-rank.
    # Mean-pooled transformer embeddings carry a large shared component from the protein-identity
    # embeddings, so healthy values there sit around 0.05-0.3; true collapse drives it towards 0.
    rel_std = float(Z.std(0).mean() / (np.sqrt((Z ** 2).mean()) + 1e-12))
    collapsed = rel_std < 0.01 or eff_rank < 2.0
    return {"emb_std": float(Z.std(0).mean()), "rel_std": rel_std, "eff_rank": eff_rank,
            "dim": Z.shape[1], "collapsed": collapsed}


# ----------------------------------------------------------------- bootstrap
def bootstrap_indices(n: int, n_boot: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def seed_mean_metric(metric_fn, per_seed_outputs, idx=None) -> float:
    vals = []
    for out in per_seed_outputs:
        v = metric_fn(out, idx)
        if np.isfinite(v):
            vals.append(v)
    return float(np.mean(vals)) if vals else np.nan


def bootstrap_ci(metric_fn, per_seed_outputs, n: int, n_boot: int, seed: int = 0):
    """95% CI over test patients for the seed-averaged metric."""
    boots = [seed_mean_metric(metric_fn, per_seed_outputs, idx)
             for idx in bootstrap_indices(n, n_boot, seed)]
    boots = np.array([b for b in boots if np.isfinite(b)])
    return (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if len(boots) else (np.nan, np.nan)


def paired_bootstrap_diff(metric_fn, outputs_a, outputs_b, n: int, n_boot: int, seed: int = 0):
    """Mean difference A - B with 95% CI and the share of resamples where A wins."""
    diffs = []
    for idx in bootstrap_indices(n, n_boot, seed):
        a = seed_mean_metric(metric_fn, outputs_a, idx)
        b = seed_mean_metric(metric_fn, outputs_b, idx)
        if np.isfinite(a) and np.isfinite(b):
            diffs.append(a - b)
    diffs = np.array(diffs)
    point = seed_mean_metric(metric_fn, outputs_a) - seed_mean_metric(metric_fn, outputs_b)
    return {"diff": float(point), "lo": float(np.percentile(diffs, 2.5)),
            "hi": float(np.percentile(diffs, 97.5)), "p_a_wins": float((diffs > 0).mean())}


def f1_from_output(out, idx=None):
    y, proba, classes = out["y"], out["proba"], out["classes"]
    if idx is not None:
        y, proba = y[idx], proba[idx]
    return f1_score(y, np.asarray(classes)[proba.argmax(1)], average="macro")


def cindex_from_output(out, idx=None):
    t, e, r = out["time"], out["event"], out["risk"]
    if idx is not None:
        t, e, r = t[idx], e[idx], r[idx]
    return c_index(t, e, r)
