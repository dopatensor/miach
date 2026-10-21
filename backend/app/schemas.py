"""Pydantic models: the API contract. Every response carries research_use_only."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RUO(BaseModel):
    research_use_only: Literal[True] = True


class Health(RUO):
    status: str
    artifacts_built_at: str


class Disease(BaseModel):
    id: str
    name: str
    enabled: bool


class Diseases(RUO):
    diseases: list[Disease]


class SplitQc(BaseModel):
    patients: int
    labelled: int
    unlabelled: int
    subtypes: dict[str, int]
    pfs_events: int


class ProteinMissing(BaseModel):
    protein: str
    gene: str
    block: str
    missing: float


class BlockMissing(BaseModel):
    block: str
    proteins: int
    missing: float


class Missingness(BaseModel):
    overall: float
    proteins_any_missing: int
    proteins_fully_missing: int
    per_protein: list[ProteinMissing]
    per_block: list[BlockMissing]


class Qc(RUO):
    disease: str
    n_patients: int
    n_proteins: int
    splits: dict[str, SplitQc]
    missingness: Missingness
    imputation: str


class MarkerRow(BaseModel):
    rank: int
    protein: str
    protein_id: str
    gene: str
    block: str
    importance: float
    importance_sd: float
    stability: float = Field(description="Fraction of bootstrap refits with this protein in the top 8")


class KnownMarker(BaseModel):
    protein: str
    gene: str
    rank: int
    of: int
    role: str


class Markers(RUO):
    disease: str
    method: str
    markers: list[MarkerRow]
    known_markers: list[KnownMarker]
    note: str


class Metrics(BaseModel):
    macro_f1: float
    balanced_acc: float
    auroc: float | None
    c_index: float | None


class FullModel(BaseModel):
    k: int
    model: str
    metrics: Metrics


class PanelMarker(BaseModel):
    protein: str
    gene: str
    block: str
    rank: int | None


class Panel(RUO):
    disease: str
    goal: Literal["subtype", "survival"]
    k: int
    markers: list[str]
    marker_details: list[PanelMarker]
    metrics: Metrics
    full_model: FullModel
    test_n: int
    test_labelled: int
    test_events: int
    preliminary: Literal[True] = True
    test_set: str = "locked"
    method: str
    c_index_note: str
    note: str | None = None
    custom: bool = False


class CustomPanelRequest(BaseModel):
    markers: list[str] = Field(min_length=1, max_length=30)
    goal: Literal["subtype", "survival"] = "subtype"


class LatentPoint(BaseModel):
    x: float
    y: float
    subtype: str
    split: Literal["train", "test"]
    id: str | None = Field(None, description="TCGA patient id; only set for locked test patients")


class Latent(RUO):
    method: str
    explained_variance: list[float]
    points: list[LatentPoint]


class ModelRow(BaseModel):
    model: str
    kind: Literal["linear", "deep"]
    f1_10: float
    f1_100: float
    production: bool


class Models(RUO):
    model_config = ConfigDict(protected_namespaces=())
    preliminary: Literal[True] = True
    metric: str
    settings: dict
    source: str
    models: list[ModelRow]
    rebuild_check: dict


class PredictRow(BaseModel):
    row: int
    sample_id: str | None
    probabilities: dict[str, float]
    top_subtype: str


class PredictQc(BaseModel):
    n_rows: int
    matched: list[str]
    missing: list[str]
    unrecognised_columns: list[str]
    imputed_note: str


class Predict(RUO):
    model_config = ConfigDict(protected_namespaces=())
    model: str
    rows: list[PredictRow]
    qc: PredictQc
    note: str


class PatientRow(BaseModel):
    id: str
    subtype: str | None = Field(description="PAM50 subtype (RNA-defined); null if not called")
    predicted: str
    confidence: float
    mismatch: bool
    pfs_months: float | None
    pfs_event: int | None


class PatientList(RUO):
    split: Literal["test"] = "test"
    k: int
    markers: list[str]
    patients: list[PatientRow]
    note: str


class PatientMarker(BaseModel):
    protein: str
    z: float
    missing: bool


class PatientDetail(PatientRow, RUO):
    split: Literal["test"] = "test"
    k: int
    probabilities: dict[str, float]
    markers: list[PatientMarker]
    note: str


class ResultRow(BaseModel):
    encoder: str
    cancer: str
    fraction: float
    macro_f1: float | None
    f1_lo: float | None
    f1_hi: float | None
    balanced_acc: float | None
    c_index: float
    c_lo: float
    c_hi: float


class Cancer(BaseModel):
    id: str
    name: str
    task: str | None = Field(None, description="Classification task; None = survival only")
    survival: str


class KnownRanks(BaseModel):
    known: dict[str, int | None] = Field(description="Gene -> rank of 198 (None = not measured / not ranked)")
    top10: list[str]


class EmbeddingHealth(BaseModel):
    emb_std: float
    rel_std: float
    eff_rank: float
    dim: int
    collapsed: bool


class Results(RUO):
    preliminary: Literal[True] = True
    test_set: str
    source: str
    cancers: list[Cancer]
    encoders: list[str]
    rows: list[ResultRow]
    known: dict[str, KnownRanks]
    health: dict[str, EmbeddingHealth] = Field(default_factory=dict, description="Per encoder, breast locked test set")
    markers: list[MarkerRow] | None = Field(None, description="Only with ?cancer=: markers_<cancer>.csv ranking")
    note: str | None = None


class CancerMarkers(RUO):
    preliminary: Literal[True] = True
    cancer: Cancer
    method: str
    markers: list[MarkerRow] = Field(description="Empty when the cancer has no classification labels (ovarian)")
    known: KnownRanks | None
    note: str | None
