import asyncio
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402


def _mock(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_post, real_get = httpx.post, httpx.get
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Client(transport=transport).post(url, **kw))
    monkeypatch.setattr(httpx, "get", lambda url, **kw: httpx.Client(transport=transport).get(url, **kw))


def test_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == {"model_health", "predict_failure", "get_machine_status", "list_active_alerts"}


def test_predict_rejects_bad_type():
    assert "error" in server.predict_failure("CNC-1", "X", 300, 310, 1500, 40, 100)


def test_predict_uses_token(monkeypatch):
    monkeypatch.setattr(server, "API_PASSWORD", "pw")
    server._token.update(value=None, expires=0)

    def handler(req):
        if req.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": "T", "expires_in": 300})
        assert req.headers["authorization"] == "Bearer T"
        return httpx.Response(200, json={"failure_probability": 0.9, "alert_level": "LARRIA"})

    _mock(monkeypatch, handler)
    out = server.predict_failure("CNC-1", "L", 300, 310, 1500, 40, 100)
    assert out["alert_level"] == "LARRIA"


def test_machine_status_trend(monkeypatch):
    hits = [{"failure_probability": p, "alert_level": "KONTUZ"} for p in (0.7, 0.5, 0.3)]
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"hits": {"hits": [{"_source": h} for h in hits]}}))
    out = server.get_machine_status("CNC-1")
    assert out["trend"] == "rising" and out["found"]


def test_alerts_dedup_per_machine(monkeypatch):
    hits = [
        {"machine_id": "A", "failure_probability": 0.6, "alert_level": "KONTUZ"},
        {"machine_id": "B", "failure_probability": 0.9, "alert_level": "LARRIA"},
        {"machine_id": "A", "failure_probability": 0.55, "alert_level": "KONTUZ"},
    ]
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"hits": {"hits": [{"_source": h} for h in hits]}}))
    out = server.list_active_alerts()
    assert out["count"] == 2 and out["alerts"][0]["machine_id"] == "B"


def test_health_down(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("no", request=req)

    _mock(monkeypatch, boom)
    assert server.model_health()["status"] == "down"
