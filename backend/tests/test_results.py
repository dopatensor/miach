import csv
import math

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
