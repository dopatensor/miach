"""Loads artifacts/ once at startup. Everything is read-only after that."""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(os.environ.get("MIACH_ARTIFACTS", ROOT / "artifacts"))
ML_DIR = Path(os.environ.get("MIACH_ML_DIR", ROOT / "ml"))

# The panel refit is the exact function the offline build used.
sys.path.insert(0, str(ML_DIR))
import miach_panel  # noqa: E402

MAX_CUSTOM_MARKERS = 30


class Store:
    def __init__(self, path: Path = ARTIFACTS):
        def load(name):
            return json.loads((path / name).read_text())

        self.meta = load("meta.json")
        self.qc = load("qc.json")
        self.markers = load("markers.json")
        self.panels = load("panels.json")
        self.latent = load("latent.json")
        self.models = load("models.json")
        self.patients = load("patients.json")
        self.patient_index = {p["id"]: i for i, p in enumerate(self.patients["patients"])}
        with np.load(path / "arrays.npz") as z:
            self.arrays = {k: z[k] for k in z.files}
        self.model = joblib.load(path / "model.joblib")

        self.panel_by_k = {p["k"]: p for p in self.panels["panels"]}
        self.marker_by_name = {m["protein"]: m for m in self.markers["markers"]}
        self.col_by_name = {name: i for i, name in enumerate(self.meta["proteins"])}
        # Accept "ESR1|ER-alpha" style ids too.
        self.col_by_name.update({pid: i for i, pid in enumerate(self.meta["protein_ids"])})
        self._refit = lru_cache(maxsize=256)(self._refit_uncached)

    def refit(self, cols: tuple[int, ...]) -> dict:
        return self._refit(cols)

    def _refit_uncached(self, cols: tuple[int, ...]) -> dict:
        return miach_panel.fit_panel(self.arrays, list(cols))


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
