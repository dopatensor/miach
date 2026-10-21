"""Non-deep baselines. These need no PyTorch."""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA

import config as C
from evaluate import fill
from .base import Encoder


class RawEncoder(Encoder):
    """Proteins as-is. With the elastic-net probe this is the 'elastic net' baseline."""
    name = "raw"
    probe_l1_ratio = 0.5

    def fit(self, ds, labelled_idx=None, seed=0):
        return self

    def embed(self, X):
        return fill(X)


class PCAEncoder(Encoder):
    """Linear compression fitted on the same pan-cancer pool the deep models pretrain on."""
    name = "pca"

    def fit(self, ds, labelled_idx=None, seed=0):
        k = self.cfg.get("dim", C.EMBED_DIM)
        self.pca = PCA(n_components=k, random_state=seed).fit(fill(ds.X_pre))
        self.log.append({"explained_variance": float(self.pca.explained_variance_ratio_.sum())})
        return self

    def embed(self, X):
        return self.pca.transform(fill(X))
