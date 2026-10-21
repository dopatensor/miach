from fastapi import APIRouter, Depends, HTTPException

from ..schemas import CancerMarkers, Results
from ..store import CANCERS, MULTI_MARKER_BOOT, Store, get_store

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/results", response_model=Results)
def results(store: Store = Depends(get_store)):
    """Four-cancer encoder comparison on each cancer's locked test set (ml/results_multi)."""
    return store.results


@router.get("/results/markers", response_model=CancerMarkers)
def cancer_markers(cancer: str, store: Store = Depends(get_store)):
    """Precomputed marker ranking for one of the four cancers (markers_<cancer>.csv)."""
    meta = next((c for c in CANCERS if c["id"] == cancer), None)
    if meta is None:
        raise HTTPException(404, f"unknown cancer {cancer!r}; use one of {[c['id'] for c in CANCERS]}")
    rows = store.multi_markers.get(cancer, [])
    return CancerMarkers(
        cancer=meta,
        method=(f"elastic net on all proteins, occlusion importance on training patients only; "
                f"stability = share of {MULTI_MARKER_BOOT} bootstrap refits with the protein in the top 8"),
        markers=rows,
        known=store.results["known"].get(cancer),
        note=None if rows else "Survival only: no public subtype labels, so there is no subtype marker ranking.",
    )
