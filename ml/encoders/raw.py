"""Elastic-net multinomial logistic regression on raw (z-scored) proteins."""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

from miach_panel import classification_metrics

C_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]


def make_probe(C: float, l1_ratio: float) -> LogisticRegression:
    return LogisticRegression(
        solver="saga", l1_ratio=l1_ratio, C=C,
        max_iter=5000, class_weight="balanced", random_state=0,
    )


class RawElasticNet:
    probe_l1_ratio = 0.5

    def fit(self, ds, cols: list[int] | None = None):
        """Choose C on the validation set (never the test set), refit on train+val."""
        self.cols = list(range(len(ds.proteins))) if cols is None else list(cols)
        self.n_classes = len(ds.classes)
        tr, va = ds.train, ds.val
        Xtr, ytr = tr.X[tr.labelled][:, self.cols], tr.y[tr.labelled]
        Xva, yva = va.X[va.labelled][:, self.cols], va.y[va.labelled]
        best = (-1.0, C_GRID[0])
        for C in C_GRID:
            m = make_probe(C, self.probe_l1_ratio).fit(Xtr, ytr)
            f1 = classification_metrics(yva, m.predict_proba(Xva), self.n_classes)["macro_f1"]
            if f1 > best[0]:
                best = (f1, C)
        self.C = best[1]
        self.val_macro_f1 = best[0]
        X = np.vstack([Xtr, Xva])
        y = np.concatenate([ytr, yva])
        self.model = make_probe(self.C, self.probe_l1_ratio).fit(X, y)
        return self

    def predict_proba(self, X_full: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X_full[:, self.cols])
