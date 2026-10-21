"""Download TCGA protein (RPPA) and clinical data, match patients, lock the splits.

Everything downstream works on the same z-scored matrices produced here, with
NaN kept for missing values so each encoder decides how to handle them.
"""
from __future__ import annotations

import pickle
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

import config as C


# ----------------------------------------------------------------- download
def _download(study: str, fname: str) -> pd.DataFrame | None:
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = C.RAW_DIR / f"{study}_{fname}"
    if not path.exists():
        url = f"{C.DATAHUB}/{study}_tcga_pan_can_atlas_2018/{fname}"
        try:
            print(f"  downloading {study}/{fname}")
            urllib.request.urlretrieve(url, path)
        except urllib.error.HTTPError as e:
            print(f"  skip {study}/{fname}: HTTP {e.code}")
            return None
    return pd.read_csv(path, sep="\t", comment="#", low_memory=False)


def load_rppa(study: str) -> pd.DataFrame | None:
    """Return a samples x proteins frame indexed by patient ID (primary tumours only)."""
    df = _download(study, "data_rppa.txt")
    if df is None:
        return None
    df = df.set_index(df.columns[0]).T
    df.index = df.index.astype(str)
    df = df[df.index.str[13:15] == "01"]                  # primary tumour samples
    df.index = df.index.str[:12]                           # sample -> patient ID
    df = df[~df.index.duplicated(keep="first")]
    return df.apply(pd.to_numeric, errors="coerce")


def load_clinical(study: str) -> pd.DataFrame:
    df = _download(study, "data_clinical_patient.txt").set_index("PATIENT_ID")
    out = pd.DataFrame(index=df.index)
    out["subtype"] = df["SUBTYPE"].str.replace(f"{study.upper()}_", "", regex=False)
    status = df[C.SURVIVAL_STATUS_COL].astype(str)
    out["event"] = np.where(status.str.startswith("1"), 1.0,
                            np.where(status.str.startswith("0"), 0.0, np.nan))
    out["time"] = pd.to_numeric(df[C.SURVIVAL_TIME_COL], errors="coerce")
    return out


# ----------------------------------------------------------------- dataset
@dataclass
class Split:
    X: np.ndarray            # z-scored, NaN = missing
    subtype: np.ndarray      # object array of str or None
    time: np.ndarray
    event: np.ndarray
    patients: np.ndarray


@dataclass
class Dataset:
    proteins: list[str]
    X_pre: np.ndarray         # pan-cancer pretraining pool (BRCA test patients excluded)
    pre_study: np.ndarray
    train: Split
    val: Split
    test: Split
    classes: list[str] = field(default_factory=list)

    @property
    def genes(self) -> list[str]:
        return [p.split("|")[0] for p in self.proteins]


def build_dataset(studies: list[str] | None = None, use_cache: bool = True) -> Dataset:
    studies = studies or C.PANCAN_STUDIES
    C.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = C.CACHE_DIR / f"dataset_{len(studies)}studies.pkl"
    if use_cache and cache.exists():
        return pickle.loads(cache.read_bytes())

    print("Loading breast cancer data")
    brca = load_rppa(C.TARGET_STUDY)
    proteins = list(brca.columns)
    clin = load_clinical(C.TARGET_STUDY).reindex(brca.index)

    # Locked, stratified, patient-level test split. Unlabelled patients form their own stratum.
    strata = clin["subtype"].fillna("unlabelled").values
    idx = np.arange(len(brca))
    tr_idx, te_idx = train_test_split(idx, test_size=C.TEST_FRACTION,
                                      random_state=C.SPLIT_SEED, stratify=strata)
    tr_idx, va_idx = train_test_split(tr_idx, test_size=C.VAL_FRACTION,
                                      random_state=C.SPLIT_SEED, stratify=strata[tr_idx])
    test_patients = set(brca.index[te_idx])

    print("Loading pan-cancer pretraining pool")
    frames, labels = [], []
    for s in studies:
        df = brca if s == C.TARGET_STUDY else load_rppa(s)
        if df is None:
            continue
        df = df.reindex(columns=proteins)               # BRCA panel; absent proteins -> NaN
        df = df[~df.index.isin(test_patients)]          # never pretrain on test patients
        frames.append(df)
        labels += [s] * len(df)
    pre = pd.concat(frames)

    # z-score with statistics from the pretraining pool only (test excluded).
    mu, sd = pre.mean(), pre.std().replace(0, 1.0)
    z = lambda d: ((d - mu) / sd).to_numpy(dtype=np.float32)

    def make(ix):
        d = brca.iloc[ix]
        c = clin.iloc[ix]
        sub = c["subtype"].astype(object).where(c["subtype"].notna(), None).to_numpy()
        return Split(z(d), sub, c["time"].to_numpy(), c["event"].to_numpy(), d.index.to_numpy())

    ds = Dataset(
        proteins=proteins,
        X_pre=z(pre),
        pre_study=np.array(labels),
        train=make(tr_idx), val=make(va_idx), test=make(te_idx),
        classes=sorted(clin["subtype"].dropna().unique()),
    )
    cache.write_bytes(pickle.dumps(ds))
    return ds


def describe(ds: Dataset) -> str:
    lines = [
        f"Proteins: {len(ds.proteins)}",
        f"Pretraining pool: {len(ds.X_pre)} tumours from {len(set(ds.pre_study))} cancer types "
        f"({np.isnan(ds.X_pre).mean():.1%} missing)",
    ]
    for name in ("train", "val", "test"):
        s = getattr(ds, name)
        lab = pd.Series([x for x in s.subtype if x is not None]).value_counts().to_dict()
        surv = np.isfinite(s.time) & np.isfinite(s.event)
        lines.append(f"BRCA {name}: {len(s.X)} patients, subtypes {lab}, "
                     f"survival {surv.sum()} ({np.nansum(s.event[surv]):.0f} events)")
    return "\n".join(lines)


if __name__ == "__main__":
    import data  # import by module name so the cache pickles `data.Dataset`, not `__main__.Dataset`
    print(data.describe(data.build_dataset()))
