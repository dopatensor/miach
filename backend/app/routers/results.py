from fastapi import APIRouter, Depends

from ..schemas import Results
from ..store import Store, get_store

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/results", response_model=Results)
def results(store: Store = Depends(get_store)):
    """Four-cancer encoder comparison on each cancer's locked test set (ml/results_multi)."""
    return store.results
