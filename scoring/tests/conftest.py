import os
import sys
from pathlib import Path

# app.config inportatu aurretik definitu behar dira
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")
os.environ.setdefault("API_USERNAME", "nifi")
os.environ.setdefault("API_PASSWORD", "test-pass")
os.environ.setdefault("MODEL_PATH", "/ez/dago/model.pkl")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.model import model_service  # noqa: E402


class FakeModel:
    """Eredu faltsua: probabilitate finko bat itzultzen du."""

    def __init__(self, prob=0.1):
        self.prob = prob

    def predict_proba(self, X):
        return [[1 - self.prob, self.prob]]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token(client):
    r = client.post("/auth/token", data={"grant_type": "password", "username": "nifi", "password": "test-pass"})
    return r.json()["access_token"]


@pytest.fixture
def fake_model():
    def _set(prob):
        model_service.model = FakeModel(prob)

    yield _set
    model_service.model = None


SAMPLE = {
    "timestamp": "2026-04-29T10:57:50Z",
    "machine_id": "CNC-039",
    "machine_type": "L",
    "air_temp_K": 299.0,
    "process_temp_K": 308.6,
    "rpm": 1587,
    "torque_Nm": 38.6,
    "tool_wear_min": 124,
}
