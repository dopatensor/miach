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
