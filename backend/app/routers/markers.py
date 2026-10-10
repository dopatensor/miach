from fastapi import APIRouter, Depends

from ..schemas import Markers
from ..store import Store, get_store
from .dataset import check_disease

router = APIRouter(prefix="/api", tags=["markers"])

CORRELATION_NOTE = (
    "Correlated markers share credit: PR ranks lower than expected because ER-alpha carries "
    "much of the same signal, so occluding PR alone costs the model little."
)


@router.get("/markers", response_model=Markers)
def markers(disease: str = Depends(check_disease), store: Store = Depends(get_store)):
    return {**store.markers, "note": CORRELATION_NOTE}
