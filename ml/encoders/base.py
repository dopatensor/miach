"""The one interface every encoder implements. Evaluation, marker ranking and the
panel refit only ever call `fit` and `embed`, so the losing encoder can be
deleted without touching anything else.
"""
from __future__ import annotations

import numpy as np


class Encoder:
    name: str = "base"
    # True if fit() uses subtype/survival labels: the runner then refits it for every
    # label fraction and seed, passing only the labelled training patients it may use.
    supervised: bool = False
    # Elastic-net mixing for the subtype probe on top of this encoder (0 = ridge).
    probe_l1_ratio: float = 0.0

    def __init__(self, **cfg):
        self.cfg = cfg
        self.log: list[dict] = []

    def fit(self, ds, labelled_idx: np.ndarray | None = None, seed: int = 0) -> "Encoder":
        """ds is a data.Dataset. X matrices contain NaN where a protein was not measured."""
        raise NotImplementedError

    def embed(self, X: np.ndarray) -> np.ndarray:
        """Map patients (rows, NaN = missing) to embeddings (rows)."""
        raise NotImplementedError
