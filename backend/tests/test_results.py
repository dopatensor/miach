import csv
import math

import pytest

from app.store import RESULTS_MULTI


def test_results_match_csv(client):
    body = client.get("/api/results").json()
    assert body["research_use_only"] is True
    with open(RESULTS_MULTI / "multi_metrics.csv") as f:
        csv_rows = list(csv.DictReader(f))
    assert len(body["rows"]) == len(csv_rows)
    for got, want in zip(body["rows"], csv_rows):
        assert got["encoder"] == want["encoder"] and got["cancer"] == want["cancer"]
        assert math.isclose(got["c_index"], float(want["c_index"]))
        if want["macro_f1"]:
            assert math.isclose(got["macro_f1"], float(want["macro_f1"]))
        else:
            assert got["macro_f1"] is None


def test_ovarian_is_survival_only(client):
    body = client.get("/api/results").json()
    ov = next(c for c in body["cancers"] if c["id"] == "ov")
    assert ov["task"] is None
    assert all(r["macro_f1"] is None for r in body["rows"] if r["cancer"] == "ov")
    assert "ov" not in body["known"]


def test_cancer_markers_match_csv(client):
    for cancer in ("brca", "lung", "crc"):
        body = client.get(f"/api/results/markers?cancer={cancer}").json()
        with open(RESULTS_MULTI / f"markers_{cancer}.csv") as f:
            first = next(csv.DictReader(f))
        assert len(body["markers"]) == 198
        assert body["markers"][0]["protein_id"] == first["protein"]
        assert math.isclose(body["markers"][0]["importance"], float(first["importance"]))


def test_ovarian_markers_empty_not_error(client):
    body = client.get("/api/results/markers?cancer=ov").json()
    assert body["markers"] == [] and body["known"] is None and "Survival only" in body["note"]
    assert client.get("/api/results/markers?cancer=gbm").status_code == 404


def test_results_health(client):
    h = client.get("/api/results").json()["health"]
    assert set(h) == {"raw", "pca", "vae", "jepa", "recon"}
    assert h["jepa"]["dim"] == 128


@pytest.mark.parametrize("cancer", ["brca", "lung", "crc", "ov"])
def test_results_per_cancer(client, cancer):
    r = client.get(f"/api/results?cancer={cancer}")
    assert r.status_code == 200
    body = r.json()
    assert body["research_use_only"] is True
    assert [c["id"] for c in body["cancers"]] == [cancer]
    assert body["rows"] and all(x["cancer"] == cancer for x in body["rows"])
    with open(RESULTS_MULTI / "multi_metrics.csv") as f:
        assert len(body["rows"]) == sum(r["cancer"] == cancer for r in csv.DictReader(f))
    if cancer == "ov":
        assert body["markers"] == [] and "Survival only" in body["note"]
        assert all(x["macro_f1"] is None for x in body["rows"])   # no classification rows
        assert body["known"] == {}
    else:
        assert len(body["markers"]) == 198 and body["note"] is None
        assert all(x["macro_f1"] is not None for x in body["rows"])


def test_results_unknown_cancer_is_404(client):
    assert client.get("/api/results?cancer=gbm").status_code == 404


def test_backend_never_imports_torch_or_encoders():
    # Fresh interpreter: start the app (loads model.joblib with ml/ on sys.path) and check modules.
    import subprocess
    import sys
    code = ("from fastapi.testclient import TestClient; from app.main import app; import sys\n"
            "with TestClient(app) as c: c.get('/api/results'); c.get('/api/panel?k=8'); c.post('/api/panel/custom', json={'markers': ['GATA3']})\n"
            "bad = [m for m in sys.modules if m == 'torch' or m.startswith('torch.') or m == 'encoders' or m.startswith('encoders.')]\n"
            "assert not bad, bad")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=str(RESULTS_MULTI.parents[1] / "backend"))
