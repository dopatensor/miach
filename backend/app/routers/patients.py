"""Locked test-split patients with their panel predictions (precomputed for k = 1..30)."""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas import PatientDetail, PatientList
from ..store import Store, get_store
from .dataset import check_disease

router = APIRouter(prefix="/api", tags=["patients"])

NOTE = ("Locked test patients only (n = 176). Predictions come from the top-k panel model, which never saw "
        "these patients. Research use only; not a diagnosis.")


def _row(store: Store, i: int, k: int) -> dict:
    p = store.patients["patients"][i]
    proba = store.patients["predictions"][k - 1][i]
    classes = store.patients["classes"]
    best = store.patients["calls"][k - 1][i]
    return {
        "id": p["id"], "subtype": p["subtype"], "predicted": classes[best], "confidence": proba[best],
        "mismatch": p["subtype"] is not None and p["subtype"] != classes[best],
        "pfs_months": p["pfs_months"], "pfs_event": p["pfs_event"],
    }


@router.get("/patients", response_model=PatientList)
def patients(disease: str = Depends(check_disease), k: int = Query(8, ge=1, le=30),
             store: Store = Depends(get_store)):
    return {
        "k": k, "markers": store.patients["markers"][:k], "note": NOTE,
        "patients": [_row(store, i, k) for i in range(len(store.patients["patients"]))],
    }


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def patient(patient_id: str, disease: str = Depends(check_disease), k: int = Query(8, ge=1, le=30),
            store: Store = Depends(get_store)):
    i = store.patient_index.get(patient_id)
    if i is None:
        raise HTTPException(404, "not a locked test patient")
    p = store.patients["patients"][i]
    names = store.patients["markers"][:k]
    return {
        **_row(store, i, k), "k": k, "note": NOTE,
        "probabilities": dict(zip(store.patients["classes"], store.patients["predictions"][k - 1][i])),
        "markers": [{"protein": m, "z": p["z"][j], "missing": m in p["missing"]} for j, m in enumerate(names)],
    }
