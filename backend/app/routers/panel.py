from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas import CustomPanelRequest, Panel
from ..store import MAX_CUSTOM_MARKERS, Store, get_store
from .dataset import check_disease

router = APIRouter(prefix="/api", tags=["panel"])

SURVIVAL_NOTE = (
    "Survival-specific marker ranking is not built yet. This is the subtype-ranked panel; "
    "its C-index (23 progression events in the test set, underpowered) is shown for reference."
)


def _response(store: Store, goal: str, markers: list[str], metrics: dict, custom: bool) -> dict:
    p = store.panels
    details = []
    for name in markers:
        m = store.marker_by_name.get(name)
        details.append({"protein": name, "gene": m["gene"] if m else "", "block": m["block"] if m else "Other",
                        "rank": m["rank"] if m else None})
    return {
        "disease": p["disease"], "goal": goal, "k": len(markers), "markers": markers,
        "marker_details": details, "metrics": metrics, "full_model": p["full_model"],
        "test_n": p["test_n"], "test_labelled": p["test_labelled"], "test_events": p["test_events"],
        "method": p["panel_model"], "c_index_note": p["c_index_note"],
        "note": SURVIVAL_NOTE if goal == "survival" else None, "custom": custom,
    }


@router.get("/panel", response_model=Panel)
def panel(
    disease: str = Depends(check_disease),
    goal: Literal["subtype", "survival"] = "subtype",
    k: int = Query(8, ge=1, le=30),
    store: Store = Depends(get_store),
):
    row = store.panel_by_k[k]
    return _response(store, goal, row["markers"], row["metrics"], custom=False)


@router.post("/panel/custom", response_model=Panel)
def custom_panel(req: CustomPanelRequest, store: Store = Depends(get_store)):
    names = list(dict.fromkeys(m.strip() for m in req.markers))
    unknown = [n for n in names if n not in store.col_by_name]
    if unknown:
        raise HTTPException(422, f"unknown proteins: {', '.join(unknown)}")
    if len(names) > MAX_CUSTOM_MARKERS:
        raise HTTPException(422, f"at most {MAX_CUSTOM_MARKERS} markers")
    cols = tuple(store.col_by_name[n] for n in names)
    canonical = [store.meta["proteins"][c] for c in cols]
    res = store.refit(cols)
    metrics = {k: (None if v != v else round(v, 4)) for k, v in res["metrics"].items()}
    return _response(store, req.goal, canonical, metrics, custom=True)
