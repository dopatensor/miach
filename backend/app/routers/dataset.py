from fastapi import APIRouter, Depends, HTTPException

from ..schemas import Diseases, Health, Latent, Qc
from ..store import Store, get_store

router = APIRouter(prefix="/api", tags=["dataset"])

DISEASES = [
    ("brca", "Breast cancer", True),
    ("luad", "Lung adenocarcinoma", False),
    ("coad", "Colorectal cancer", False),
    ("ov", "Ovarian cancer", False),
    ("gbm", "Glioblastoma", False),
]


def check_disease(disease: str = "brca") -> str:
    if disease != "brca":
        raise HTTPException(404, f"disease {disease!r} is not available yet; only 'brca' is enabled")
    return disease


@router.get("/health", response_model=Health)
def health(store: Store = Depends(get_store)):
    return Health(status="ok", artifacts_built_at=store.meta["built_at"])


@router.get("/diseases", response_model=Diseases)
def diseases():
    return Diseases(diseases=[{"id": i, "name": n, "enabled": e} for i, n, e in DISEASES])


@router.get("/dataset/qc", response_model=Qc)
def qc(disease: str = Depends(check_disease), store: Store = Depends(get_store)):
    return store.qc


@router.get("/latent", response_model=Latent)
def latent(disease: str = Depends(check_disease), store: Store = Depends(get_store)):
    return store.latent
