"""Miach API. Serves precomputed artifacts from memory and the built frontend from /."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import dataset, markers, models, panel, patients, predict
from .store import ROOT, get_store

FRONTEND_DIST = Path(os.environ.get("MIACH_FRONTEND_DIST", ROOT / "frontend" / "dist"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_store()  # load artifacts once, fail fast if missing
    yield


app = FastAPI(
    title="Miach API",
    description="Biomarker panel designer. Research use only; not for diagnosis or treatment decisions.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("MIACH_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
for r in (dataset.router, markers.router, panel.router, patients.router, models.router, predict.router):
    app.include_router(r)

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (FRONTEND_DIST / path).resolve()
        if path and f.is_file() and FRONTEND_DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(FRONTEND_DIST / "index.html")
