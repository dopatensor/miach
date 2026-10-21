import pytest

from app import schemas

GETS = [
    ("/api/health", schemas.Health),
    ("/api/diseases", schemas.Diseases),
    ("/api/dataset/qc?disease=brca", schemas.Qc),
    ("/api/markers?disease=brca", schemas.Markers),
    ("/api/panel?disease=brca&goal=subtype&k=8", schemas.Panel),
    ("/api/latent?disease=brca", schemas.Latent),
    ("/api/models", schemas.Models),
    ("/api/results", schemas.Results),
]


@pytest.mark.parametrize("path,model", GETS)
def test_get_contract(client, path, model):
    r = client.get(path)
    assert r.status_code == 200
    body = r.json()
    assert body["research_use_only"] is True
    model.model_validate(body)


def test_known_markers_present(client):
    known = {k["protein"]: k["rank"] for k in client.get("/api/markers").json()["known_markers"]}
    assert {"ER-alpha", "HER2", "GATA3"} <= set(known)
    assert known["ER-alpha"] <= 10


def test_diseases_only_brca_enabled(client):
    ds = client.get("/api/diseases").json()["diseases"]
    assert [d["id"] for d in ds if d["enabled"]] == ["brca"]


def test_qc_split_sizes(client):
    s = client.get("/api/dataset/qc").json()["splits"]
    assert (s["train"]["patients"], s["val"]["patients"], s["test"]["patients"]) == (595, 105, 176)
    assert s["test"]["pfs_events"] == 23
