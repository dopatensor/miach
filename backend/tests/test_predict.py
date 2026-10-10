import io

from app import schemas


def test_predict_with_missing_columns(client):
    csv = "sample,ER-alpha,ESR1|ER-alpha_pS118,HER2,GATA3,not_a_protein\ns1,2.0,0.5,-0.3,1.5,9\ns2,-2.0,-0.5,3.0,-1.0,9\n"
    r = client.post("/api/predict", files={"file": ("x.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    schemas.Predict.model_validate(body)
    assert body["research_use_only"] is True
    qc = body["qc"]
    assert set(qc["matched"]) == {"ER-alpha", "ER-alpha_pS118", "HER2", "GATA3"}
    assert len(qc["missing"]) == 198 - 4
    assert qc["unrecognised_columns"] == ["not_a_protein"]
    assert [row["sample_id"] for row in body["rows"]] == ["s1", "s2"]
    for row in body["rows"]:
        assert abs(sum(row["probabilities"].values()) - 1) < 1e-3


def test_predict_rejects_no_proteins(client):
    r = client.post("/api/predict", files={"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")})
    assert r.status_code == 422
