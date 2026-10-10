from fastapi import APIRouter, Depends

from ..schemas import Models
from ..store import Store, get_store

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/models", response_model=Models)
def models(store: Store = Depends(get_store)):
    return store.models
