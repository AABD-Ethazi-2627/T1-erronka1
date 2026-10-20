import pytest

from tests.conftest import SAMPLE


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["model_loaded"] is False


def test_token_okerra(client):
    r = client.post("/auth/token", data={"grant_type": "password", "username": "nifi", "password": "x"})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_grant"


def test_refresh_flow(client):
    r = client.post("/auth/token", json={"grant_type": "password", "username": "nifi", "password": "test-pass"})
    refresh = r.json()["refresh_token"]
    r2 = client.post("/auth/token", data={"grant_type": "refresh_token", "refresh_token": refresh})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_refresh_ez_da_access(client, token):
    # access tokena ez da refresh gisa onartu behar
    r = client.post("/auth/token", data={"grant_type": "refresh_token", "refresh_token": token})
    assert r.status_code == 400


def test_predict_tokenik_gabe(client):
    assert client.post("/predict", json=SAMPLE).status_code == 401


def test_predict_eredurik_gabe(client, token):
    assert client.post("/predict", json=SAMPLE, headers=auth(token)).status_code == 503


@pytest.mark.parametrize("prob,maila,predicted", [(0.1, "OK", False), (0.5, "OK", False), (0.8, "KONTUZ", True), (0.95, "LARRIA", True)])
def test_predict_alerta_mailak(client, token, fake_model, prob, maila, predicted):
    fake_model(prob)
    r = client.post("/predict", json=SAMPLE, headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["alert_level"] == maila
    assert body["failure_predicted"] is predicted
    assert body["machine_id"] == "CNC-039"
    assert body["timestamp"] == SAMPLE["timestamp"]


def test_predict_timestamp_gabe(client, token, fake_model):
    fake_model(0.1)
    body = {k: v for k, v in SAMPLE.items() if k != "timestamp"}
    r = client.post("/predict", json=body, headers=auth(token))
    assert r.status_code == 200
    assert r.json()["timestamp"].endswith("Z")


@pytest.mark.parametrize("field,value", [("machine_type", "X"), ("torque_Nm", "abc")])
def test_predict_balio_okerrak(client, token, fake_model, field, value):
    fake_model(0.1)
    r = client.post("/predict", json={**SAMPLE, field: value}, headers=auth(token))
    assert r.status_code == 422
