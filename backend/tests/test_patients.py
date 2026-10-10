import json

from app import schemas
from app.store import ARTIFACTS

PANELS = json.loads((ARTIFACTS / "panels.json").read_text())


def test_only_locked_test_patients(client):
    body = client.get("/api/patients", params={"k": 8}).json()
    schemas.PatientList.model_validate(body)
    assert body["research_use_only"] is True
    assert len(body["patients"]) == 176
    assert sum(p["pfs_event"] == 1 for p in body["patients"]) == 23


def test_patient_predictions_reproduce_panel_macro_f1(client):
    from sklearn.metrics import f1_score
    for k in (1, 8, 30):
        rows = [p for p in client.get("/api/patients", params={"k": k}).json()["patients"] if p["subtype"]]
        f1 = f1_score([r["subtype"] for r in rows], [r["predicted"] for r in rows], average="macro",
                      labels=["LumA", "LumB", "Basal", "Her2", "Normal"], zero_division=0)
        assert abs(f1 - PANELS["panels"][k - 1]["metrics"]["macro_f1"]) < 1e-3


def test_patient_detail(client):
    pid = client.get("/api/patients").json()["patients"][0]["id"]
    body = client.get(f"/api/patients/{pid}", params={"k": 5}).json()
    schemas.PatientDetail.model_validate(body)
    assert [m["protein"] for m in body["markers"]] == PANELS["panels"][4]["markers"]
    assert abs(sum(body["probabilities"].values()) - 1) < 0.01


def test_training_patients_are_not_served(client):
    latent = client.get("/api/latent").json()["points"]
    train_ids = [p["id"] for p in latent if p["split"] == "train"]
    assert train_ids and all(i is None for i in train_ids)
    assert client.get("/api/patients/NOT-A-PATIENT").status_code == 404
