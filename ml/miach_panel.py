"""Panel model shared by the offline build and the online API.

A panel model is an L2 multinomial logistic regression on a handful of proteins.
C is chosen on the validation split, then the model is refit on train + val and
scored on the locked test split. This file is imported by backend/app so a
custom panel refit is bit-for-bit the same procedure as the precomputed panels.
Only numpy and scikit-learn; no pandas, no data download.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, roc_auc_score

C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)


def _lr(C: float) -> LogisticRegression:
    return LogisticRegression(C=C, max_iter=2000, class_weight="balanced", tol=1e-8)


def classification_metrics(y: np.ndarray, proba: np.ndarray, n_classes: int) -> dict:
    pred = proba.argmax(axis=1)
    labels = list(range(n_classes))
    try:
        auroc = float(roc_auc_score(y, proba, multi_class="ovr", average="macro", labels=labels))
    except ValueError:
        auroc = float("nan")
    return {
        "macro_f1": float(f1_score(y, pred, average="macro", labels=labels, zero_division=0)),
        "balanced_acc": float(balanced_accuracy_score(y, pred)),
        "auroc": auroc,
    }


def c_index(time: np.ndarray, event: np.ndarray, risk: np.ndarray) -> float:
    """Harrell's concordance index (higher risk = earlier event)."""
    ok = ~np.isnan(time) & (event >= 0)
    time, event, risk = time[ok], event[ok], risk[ok]
    num = den = 0.0
    for i in np.where(event == 1)[0]:
        later = time > time[i]
        den += later.sum()
        num += (risk[i] > risk[later]).sum() + 0.5 * (risk[i] == risk[later]).sum()
    return float(num / den) if den else float("nan")


def fit_panel(arrays: dict, cols: list[int]) -> dict:
    """Fit and score a panel on the given protein column indices.

    `arrays` holds the z-scored split matrices and labels:
    X_train, y_train, X_val, y_val, X_test, y_test, t_test, e_test, subtype_hazard.
    Labels are -1 for patients without a PAM50 call; they are skipped.
    """
    n_classes = len(arrays["subtype_hazard"])

    def lab(split):
        X, y = arrays[f"X_{split}"], arrays[f"y_{split}"]
        keep = y >= 0
        return X[keep][:, cols], y[keep]

    Xtr, ytr = lab("train")
    Xva, yva = lab("val")
    Xte, yte = lab("test")

    best_f1, best_C = -1.0, C_GRID[0]
    for C in C_GRID:
        m = _lr(C).fit(Xtr, ytr)
        f1 = classification_metrics(yva, m.predict_proba(Xva), n_classes)["macro_f1"]
        if f1 > best_f1 + 1e-12:
            best_f1, best_C = f1, C
    model = _lr(best_C).fit(np.vstack([Xtr, Xva]), np.concatenate([ytr, yva]))

    metrics = classification_metrics(yte, model.predict_proba(Xte), n_classes)
    # Survival: risk = expected training-set progression rate under the predicted subtype mix.
    # The hazard per subtype comes from training patients only.
    proba_all = model.predict_proba(arrays["X_test"][:, cols])
    risk = proba_all @ np.asarray(arrays["subtype_hazard"])
    metrics["c_index"] = c_index(arrays["t_test"], arrays["e_test"], risk)
    return {"metrics": metrics, "C": best_C, "val_macro_f1": best_f1, "test_proba": proba_all}
