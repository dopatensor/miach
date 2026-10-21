"""Loads artifacts/ once at startup. Everything is read-only after that."""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(os.environ.get("MIACH_ARTIFACTS", ROOT / "artifacts"))
ML_DIR = Path(os.environ.get("MIACH_ML_DIR", ROOT / "ml"))
RESULTS_MULTI = Path(os.environ.get("MIACH_RESULTS_MULTI", ML_DIR / "results_multi"))

# The panel refit is the exact function the offline build used.
sys.path.insert(0, str(ML_DIR))
import miach_panel  # noqa: E402

MAX_CUSTOM_MARKERS = 30

# Mirrors ml/cancers.py CANCERS (not imported: it pulls in the training data loaders).
CANCERS = [
    {"id": "brca", "name": "Breast", "task": "PAM50 subtype (5 classes)", "survival": "PFS"},
    {"id": "lung", "name": "Lung", "task": "Adenocarcinoma vs squamous (2 classes)", "survival": "OS"},
    {"id": "crc", "name": "Colorectal", "task": "Molecular subtype CIN/GS/MSI/POLE (4 classes)", "survival": "PFS"},
    {"id": "ov", "name": "Ovarian", "task": None, "survival": "OS"},
]
RESULT_FIELDS = ("macro_f1", "f1_lo", "f1_hi", "balanced_acc", "c_index", "c_lo", "c_hi", "fraction")


def _num(v: str) -> float | None:
    if v == "":
        return None
    x = float(v)
    return None if math.isnan(x) else x


# run_multi.py ranks markers with --marker-boot (default 5); stability values are multiples of 1/5.
MULTI_MARKER_BOOT = 5


def load_multi_markers(path: Path = RESULTS_MULTI) -> dict:
    """markers_<cancer>.csv -> ranking rows. Ovarian has no file (no subtype labels to rank against)."""
    out = {}
    for c in CANCERS:
        f = path / f"markers_{c['id']}.csv"
        if not f.exists():
            continue
        with open(f, newline="") as fh:
            out[c["id"]] = [{
                "rank": int(r["rank"]),
                "protein": r["protein"].split("|")[-1],
                "protein_id": r["protein"],
                "gene": r["gene"],
                "block": r["block"].replace("_", " "),
                "importance": float(r["importance"]),
                "importance_sd": float(r["importance_sd"]),
                "stability": float(r["stability_top8"]),
            } for r in csv.DictReader(fh)]
    return out


def load_results(path: Path = RESULTS_MULTI) -> dict:
    with open(path / "multi_metrics.csv", newline="") as f:
        rows = [{"encoder": r["encoder"], "cancer": r["cancer"], **{k: _num(r[k]) for k in RESULT_FIELDS}}
                for r in csv.DictReader(f)]
    known = {c["id"]: json.loads((path / f"known_{c['id']}.json").read_text())
             for c in CANCERS if (path / f"known_{c['id']}.json").exists()}
    return {
        "test_set": "locked test set (per cancer, patient-level, fixed seed)",
        "source": "ml/run_multi.py -> ml/results_multi/multi_metrics.csv",
        "cancers": CANCERS,
        "encoders": list(dict.fromkeys(r["encoder"] for r in rows)),
        "rows": rows,
        "known": known,
    }


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
        self.results = load_results()
        self.multi_markers = load_multi_markers()
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
