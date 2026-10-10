"""Score an uploaded CSV with the full elastic-net subtype model. Research use only."""
import io

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..schemas import Predict
from ..store import Store, get_store

router = APIRouter(prefix="/api", tags=["predict"])

MAX_BYTES = 5_000_000
MAX_ROWS = 5000


@router.post("/predict", response_model=Predict)
async def predict(file: UploadFile = File(...), store: Store = Depends(get_store)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "file larger than 5 MB")
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, f"could not parse CSV: {e}") from e
    if df.empty:
        raise HTTPException(422, "CSV has no rows")
    if len(df) > MAX_ROWS:
        raise HTTPException(422, f"at most {MAX_ROWS} rows")

    m = store.model
    proteins = store.meta["proteins"]
    id_col = None
    first = df.columns[0]
    if first not in store.col_by_name and not pd.api.types.is_numeric_dtype(df[first]):
        id_col = first

    matched: dict[int, str] = {}
    unrecognised = []
    for c in df.columns:
        if c == id_col:
            continue
        idx = store.col_by_name.get(str(c).strip())
        if idx is None:
            unrecognised.append(str(c))
        else:
            matched[idx] = c

    if not matched:
        raise HTTPException(422, "no recognised protein columns; use RPPA names such as 'ER-alpha' or 'ESR1|ER-alpha'")

    X = np.full((len(df), len(proteins)), np.nan)
    for idx, c in matched.items():
        X[:, idx] = pd.to_numeric(df[c], errors="coerce").to_numpy()
    X = np.where(np.isnan(X), m["median"], X)
    Z = (X - m["mean"]) / m["std"]
    proba = m["model"].predict_proba(Z)

    rows = [
        {"row": i, "sample_id": None if id_col is None else str(df[id_col].iloc[i]),
         "probabilities": {c: round(float(p), 4) for c, p in zip(m["classes"], proba[i])},
         "top_subtype": m["classes"][int(proba[i].argmax())]}
        for i in range(len(df))
    ]
    return {
        "model": "Elastic net on all 198 RPPA proteins (TCGA BRCA)",
        "rows": rows,
        "qc": {
            "n_rows": len(df),
            "matched": [proteins[i] for i in sorted(matched)],
            "missing": [p for i, p in enumerate(proteins) if i not in matched],
            "unrecognised_columns": unrecognised,
            "imputed_note": "Missing proteins and empty cells are filled with the training-set median. "
                            "Values must be on the TCGA RPPA (normalised log2) scale.",
        },
        "note": "Research use only. Candidate subtype probabilities, not a diagnosis.",
    }
