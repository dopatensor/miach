import json

import pytest

from app.store import ARTIFACTS

PANELS = json.loads((ARTIFACTS / "panels.json").read_text())


def test_panel_k8_matches_artifact(client):
    r = client.get("/api/panel", params={"disease": "brca", "goal": "subtype", "k": 8})
    assert r.status_code == 200
    body = r.json()
    row = next(p for p in PANELS["panels"] if p["k"] == 8)
    assert body["k"] == 8
    assert body["markers"] == row["markers"]
    assert body["metrics"] == row["metrics"]
    assert body["test_n"] == 176
    assert body["preliminary"] is True


def test_custom_panel_reproduces_k8(client):
    row = next(p for p in PANELS["panels"] if p["k"] == 8)
    r = client.post("/api/panel/custom", json={"markers": row["markers"]})
    assert r.status_code == 200
    assert abs(r.json()["metrics"]["macro_f1"] - row["metrics"]["macro_f1"]) < 1e-6


@pytest.mark.parametrize("k", [1, 15, 30])
def test_every_k_is_precomputed(client, k):
    r = client.get("/api/panel", params={"k": k})
    assert r.status_code == 200
    assert len(r.json()["markers"]) == k


def test_k_out_of_range(client):
    assert client.get("/api/panel", params={"k": 31}).status_code == 422
    assert client.get("/api/panel", params={"k": 0}).status_code == 422


def test_survival_goal_says_ranking_not_built(client):
    body = client.get("/api/panel", params={"goal": "survival", "k": 8}).json()
    assert "not built yet" in body["note"]
    assert body["metrics"]["c_index"] is not None


def test_custom_rejects_unknown_and_too_many(client):
    assert client.post("/api/panel/custom", json={"markers": ["NOT_A_PROTEIN"]}).status_code == 422
    many = [m["protein"] for m in client.get("/api/markers").json()["markers"][:31]]
    assert client.post("/api/panel/custom", json={"markers": many}).status_code == 422


def test_disabled_disease_404(client):
    assert client.get("/api/panel", params={"disease": "luad"}).status_code == 404
