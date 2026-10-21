"""Four-cancer setup: breast, lung, ovarian, colorectal.

Each cancer gets a classification task (when public labels exist) and a survival task.
Deep encoders are pretrained ONCE on a shared pan-cancer pool that excludes the locked
test patients of all four cancers, so one pretrained model is fair to use on every cancer.

Public-data limits (stated, not hidden):
  - Lung: adenocarcinoma has no molecular subtypes, so the task is LUAD vs LUSC (histology).
    Survival = overall survival (LUSC has no PFS in the files we can reach).
  - Ovarian: no subtype labels are available in the public files we can reach -> survival only (OS).
  - Colorectal: TCGA molecular subtypes CIN / GS / MSI / POLE (colon and rectum merged); PFS.
  - Breast: PAM50 subtypes; PFS.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config as C
from data import Split, load_rppa

CANCERS = {
    "brca": {"name": "Breast", "task": "PAM50 subtype (5 classes)", "survival": "PFS"},
    "lung": {"name": "Lung", "task": "Adenocarcinoma vs squamous (2 classes)", "survival": "OS"},
    "ov": {"name": "Ovarian", "task": None, "survival": "OS"},
    "crc": {"name": "Colorectal", "task": "Molecular subtype CIN/GS/MSI/POLE (4 classes)", "survival": "PFS"},
}
ALT_BASE = "https://media.githubusercontent.com/media/cBioPortal/datahub/master/public"


def _read(path_or_url):
    return pd.read_csv(path_or_url, sep="\t", comment="#", low_memory=False)


def _clin(study_file, url=None):
    p = C.RAW_DIR / study_file
    if not p.exists():
        import urllib.request
        urllib.request.urlretrieve(url, p)
    return _read(p).drop_duplicates("PATIENT_ID").set_index("PATIENT_ID")


def _status(s):
    s = s.astype(str)
    return np.where(s.str.startswith("1"), 1.0, np.where(s.str.startswith("0"), 0.0, np.nan))


def _surv(df, kind):
    return pd.DataFrame({"event": _status(df[f"{kind}_STATUS"]),
                         "time": pd.to_numeric(df[f"{kind}_MONTHS"], errors="coerce")}, index=df.index)


def pancan_url(study):
    return f"{ALT_BASE}/{study}_tcga_pan_can_atlas_2018/data_clinical_patient.txt"


def load_cancer(key):
    """Return (rppa frame patients x proteins, clinical frame with subtype/event/time)."""
    if key == "brca":
        X = load_rppa("brca")
        c = _clin("brca_data_clinical_patient.txt", pancan_url("brca"))
        lab = c["SUBTYPE"].str.replace("BRCA_", "", regex=False)
        clin = _surv(c, "PFS").assign(subtype=lab)
    elif key == "crc":
        X = load_rppa("coadread")
        c = _clin("coadread_data_clinical_patient.txt", pancan_url("coadread"))
        lab = c["SUBTYPE"].str.split("_").str[-1]
        clin = _surv(c, "PFS").assign(subtype=lab)
    elif key == "lung":
        a, b = load_rppa("luad"), load_rppa("lusc")
        X = pd.concat([a, b[~b.index.isin(a.index)]])
        ca = _clin("luad_data_clinical_patient.txt", pancan_url("luad"))
        cb = _clin("alt_lusc_tcga_data_clinical_patient.txt", f"{ALT_BASE}/lusc_tcga/data_clinical_patient.txt")
        surv = pd.concat([_surv(ca, "OS"), _surv(cb, "OS")])
        surv = surv[~surv.index.duplicated()]
        lab = pd.Series(["LUAD"] * len(a) + ["LUSC"] * (len(X) - len(a)), index=X.index)
        clin = surv.reindex(X.index).assign(subtype=lab)
    elif key == "ov":
        X = load_rppa("ov")
        c = _clin("alt_ov_tcga_data_clinical_patient.txt", f"{ALT_BASE}/ov_tcga/data_clinical_patient.txt")
        clin = _surv(c, "OS").assign(subtype=None)
    else:
        raise KeyError(key)
    return X, clin.reindex(X.index)


@dataclass
class MultiDataset:
    proteins: list
    X_pre: np.ndarray
    splits: dict          # key -> {"train": Split, "test": Split, "classes": [...]}
    pool_n_studies: int

    # encoders read ds.X_pre and ds.proteins only, so this object can be passed to fit()


def build_multi(use_cache=True) -> MultiDataset:
    cache = C.CACHE_DIR / "multi4.pkl"
    if use_cache and cache.exists():
        return pickle.loads(cache.read_bytes())
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    proteins = list(load_rppa("brca").columns)
    raw, test_ids = {}, set()
    for key in CANCERS:
        X, clin = load_cancer(key)
        X = X.reindex(columns=proteins)
        strata = clin["subtype"].fillna("none").astype(str).values
        _, counts = np.unique(strata, return_counts=True)
        strat = strata if counts.min() >= 2 else None
        tr, te = train_test_split(np.arange(len(X)), test_size=C.TEST_FRACTION,
                                  random_state=C.SPLIT_SEED, stratify=strat)
        raw[key] = (X, clin, tr, te)
        test_ids |= set(X.index[te])

    frames = []
    for s in C.PANCAN_STUDIES:
        df = load_rppa(s)
        if df is None:
            continue
        frames.append(df.reindex(columns=proteins))
    pool = pd.concat(frames)
    pool = pool[~pool.index.duplicated()]
    pool = pool[~pool.index.isin(test_ids)]            # no test patient from any cancer
    mu, sd = pool.mean(), pool.std().replace(0, 1.0)
    z = lambda d: ((d - mu) / sd).to_numpy(dtype=np.float32)

    splits = {}
    for key, (X, clin, tr, te) in raw.items():
        def mk(ix):
            c = clin.iloc[ix]
            sub = c["subtype"].astype(object).where(c["subtype"].notna(), None).to_numpy()
            return Split(z(X.iloc[ix]), sub, c["time"].to_numpy(dtype=float),
                         c["event"].to_numpy(dtype=float), X.index[ix].to_numpy())
        classes = sorted(clin["subtype"].dropna().unique()) if clin["subtype"].notna().any() else []
        splits[key] = {"train": mk(tr), "test": mk(te), "classes": classes}

    ds = MultiDataset(proteins, z(pool), splits, len(frames))
    cache.write_bytes(pickle.dumps(ds))
    return ds


def describe(ds):
    out = [f"Pretraining pool: {len(ds.X_pre)} tumours, {ds.pool_n_studies} studies (all 4 test sets excluded)"]
    for k, s in ds.splits.items():
        tr, te = s["train"], s["test"]
        lab = pd.Series([x for x in te.subtype if x is not None]).value_counts().to_dict()
        ok = np.isfinite(te.time) & np.isfinite(te.event)
        out.append(f"{CANCERS[k]['name']:<11} train {len(tr.X)}, test {len(te.X)}; test labels {lab or 'none'}; "
                   f"test survival {ok.sum()} ({np.nansum(te.event[ok]):.0f} events, {CANCERS[k]['survival']})")
    return "\n".join(out)


if __name__ == "__main__":
    import cancers
    print(cancers.describe(cancers.build_multi(use_cache=False)))
