"""Download TCGA BRCA RPPA + clinical data and build patient-level splits.

Missing values are imputed with the training-set median, then every protein is
z-scored with training-set parameters only. Proteins entirely missing in the
training set are imputed to 0 (the training mean after z-scoring).
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import build_config as config


@dataclass
class Split:
    ids: list[str]
    X: np.ndarray          # z-scored, imputed proteins (n x p)
    y: np.ndarray          # class index, -1 where subtype unknown
    pfs_time: np.ndarray   # months, NaN if unknown
    pfs_event: np.ndarray  # 1 progression, 0 censored, -1 unknown

    @property
    def labelled(self) -> np.ndarray:
        return self.y >= 0


@dataclass
class Dataset:
    proteins: list[str]
    genes: list[str]
    classes: list[str]
    train: Split
    val: Split
    test: Split
    mean: np.ndarray       # training-set z-score parameters (after imputation)
    std: np.ndarray
    median: np.ndarray     # training-set imputation values (raw scale)
    missing_raw: pd.Series = field(repr=False)  # fraction missing per protein, all patients
    source_url: str = ""


def _download(name: str) -> str:
    config.CACHE_DIR.mkdir(exist_ok=True)
    path = config.CACHE_DIR / name
    if not path.exists():
        url = f"{config.DATAHUB}/{config.STUDY}/{name}"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, path)
    return str(path)


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (rppa: patients x proteins, clinical indexed by patient)."""
    rppa = pd.read_csv(_download("data_rppa.txt"), sep="\t", index_col=0).T
    rppa.index = [s[:12] for s in rppa.index]
    rppa = rppa[~rppa.index.duplicated()]
    clin = pd.read_csv(_download("data_clinical_patient.txt"), sep="\t", comment="#")
    clin = clin.set_index("PATIENT_ID").reindex(rppa.index)
    return rppa, clin


def _split_ids(ids: list[str]) -> tuple[list[str], list[str], list[str]]:
    rng = np.random.default_rng(config.SEED)
    perm = list(rng.permutation(sorted(ids)))
    test = perm[: config.N_TEST]
    val = perm[config.N_TEST : config.N_TEST + config.N_VAL]
    train = perm[config.N_TEST + config.N_VAL :]
    return train, val, test


def build_dataset() -> Dataset:
    rppa, clin = load_raw()
    proteins = list(rppa.columns)
    genes = [p.split("|")[0] for p in proteins]

    subtype = clin["SUBTYPE"].str.replace("BRCA_", "", regex=False)
    y_all = subtype.map({c: i for i, c in enumerate(config.CLASSES)}).fillna(-1).astype(int)
    pfs_time = pd.to_numeric(clin["PFS_MONTHS"], errors="coerce")
    pfs_event = clin["PFS_STATUS"].map(lambda s: int(str(s)[0]) if isinstance(s, str) else -1)

    train_ids, val_ids, test_ids = _split_ids(list(rppa.index))
    raw_train = rppa.loc[train_ids]
    median = raw_train.median().fillna(0.0).to_numpy()
    imputed_train = raw_train.fillna(pd.Series(median, index=proteins))
    mean = imputed_train.mean().to_numpy()
    std = imputed_train.std(ddof=0).replace(0, 1.0).fillna(1.0).to_numpy()

    def make(ids: list[str]) -> Split:
        raw = rppa.loc[ids].to_numpy(dtype=float)
        X = transform(raw, median, mean, std)
        return Split(
            ids=ids,
            X=X,
            y=y_all.loc[ids].to_numpy(),
            pfs_time=pfs_time.loc[ids].to_numpy(dtype=float),
            pfs_event=pfs_event.loc[ids].to_numpy(dtype=int),
        )

    return Dataset(
        proteins=proteins,
        genes=genes,
        classes=list(config.CLASSES),
        train=make(train_ids),
        val=make(val_ids),
        test=make(test_ids),
        mean=mean,
        std=std,
        median=median,
        missing_raw=rppa.isna().mean(),
        source_url=f"{config.DATAHUB}/{config.STUDY}",
    )


def transform(raw: np.ndarray, median: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """Impute with training medians, then z-score with training parameters."""
    raw = np.where(np.isnan(raw), median, raw)
    return (raw - mean) / std
