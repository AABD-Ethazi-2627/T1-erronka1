import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import guard  # noqa: E402
import server  # noqa: E402

SECRET = "S3cr3t-Pa55word-XYZ"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJuaWZpIn0.abcdefghijklmnop"


@pytest.fixture(autouse=True)
def _secret_env(monkeypatch):
    monkeypatch.setenv("API_PASSWORD", SECRET)


def _mock(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Client(transport=transport).post(url, **kw))
    monkeypatch.setattr(httpx, "get", lambda url, **kw: httpx.Client(transport=transport).get(url, **kw))


def _dump(out) -> str:
    return json.dumps(out)


def test_health_drops_unknown_fields(monkeypatch):
    body = {"status": "ok", "model_loaded": True, "model_path": "/models/x.pkl", "jwt": JWT, "db": f"user:{SECRET}@10.0.0.5"}
    _mock(monkeypatch, lambda req: httpx.Response(200, json=body))
    out = server.model_health()
    assert out == {"status": "ok", "model_loaded": True}


def test_predict_drops_extra_fields_and_secrets(monkeypatch):
    monkeypatch.setattr(server, "API_PASSWORD", SECRET)
    server._token.update(value=None, expires=0)

    def handler(req):
        if req.url.path == "/auth/token":
            return httpx.Response(200, json={"access_token": JWT, "expires_in": 300})
        return httpx.Response(
            200,
            json={"failure_probability": 0.9, "alert_level": "LARRIA", "machine_id": "CNC-1", "access_token": JWT, "note": SECRET},
        )

    _mock(monkeypatch, handler)
    out = server.predict_failure("CNC-1", "L", 300, 310, 1500, 40, 100)
    assert set(out) == {"failure_probability", "alert_level", "machine_id"}
    assert JWT not in _dump(out) and SECRET not in _dump(out)


def test_error_text_never_returned(monkeypatch):
    def boom(req):
        raise httpx.ConnectError(f"cannot reach http://admin:{SECRET}@10.1.2.3:9200", request=req)

    _mock(monkeypatch, boom)
    out = server.get_machine_status("CNC-1")
    assert out == {"error": "service_unreachable"}
    out = server.list_active_alerts()
    assert out == {"error": "service_unreachable"}


def test_http_status_error_is_code_only(monkeypatch):
    _mock(monkeypatch, lambda req: httpx.Response(401, text=f"bad password {SECRET}"))
    out = server.get_machine_status("CNC-1")
    assert out == {"error": "http_401"}


def test_health_down_has_no_infra_info(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("nope", request=req)

    _mock(monkeypatch, boom)
    assert server.model_health() == {"status": "down"}


def test_machine_id_is_validated_before_any_request(monkeypatch):
    def fail(req):
        raise AssertionError("ez luke eskaerarik egin behar")

    _mock(monkeypatch, fail)
    for bad in ("", "CNC 1", 'x"}, "query":{', "a" * 33, "me@mail.com"):
        assert "error" in server.get_machine_status(bad)
        assert "error" in server.predict_failure(bad, "L", 300, 310, 1500, 40, 100)


def test_non_finite_numbers_rejected():
    assert "error" in server.predict_failure("CNC-1", "L", float("nan"), 310, 1500, 40, 100)


def test_es_unknown_fields_and_bad_values_are_dropped(monkeypatch):
    hits = [
        {"machine_id": "CNC-1", "failure_probability": 0.7, "alert_level": "LARRIA", "timestamp": "2026-10-30T07:27:23Z", "owner": "ane@firma.eus", "pw": SECRET},
        {"machine_id": f"CNC-{SECRET}-EVIL@x.com", "failure_probability": 0.6, "alert_level": "KONTUZ"},
    ]
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"hits": {"hits": [{"_source": h} for h in hits]}}))
    out = server.get_machine_status("CNC-1")
    text = _dump(out)
    assert SECRET not in text and "ane@firma.eus" not in text and "owner" not in text
    assert out["predictions"][0] == {
        "machine_id": "CNC-1", "failure_probability": 0.7, "alert_level": "LARRIA", "timestamp": "2026-10-30T07:27:23Z"
    }
    assert "machine_id" not in out["predictions"][1]  # ID baliogabea baztertua


def test_redact_text_patterns():
    for leaked in (
        JWT,
        "Authorization: Bearer abcdefghijkl12345",
        "123456789:AAH-abcdefghijklmnopqrstuvwxyz012345",
        "https://admin:hunter2@host/x",
        "password=hunter2",
        "contact ane@firma.eus",
        "server 192.168.75.150",
        "a" * 40,
        f"x {SECRET} y",
    ):
        assert REDACTED_ in guard.redact_text(leaked)


REDACTED_ = guard.REDACTED


def test_dotenv_secret_values_are_redacted(monkeypatch):
    monkeypatch.setenv("SMB_PASSWORD", "Smb-Sup3r-secret")
    monkeypatch.setenv("SMB_IP", "172.16.9.9")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_SECONDS", "3600")
    out = guard.redact_text("pw=Smb-Sup3r-secret host 172.16.9.9 ttl 3600")
    assert "Smb-Sup3r-secret" not in out and "172.16.9.9" not in out
    assert "3600" in out  # iraungitze-denbora ez da sekretua


def test_fail_closed_on_unexpected_output():
    @guard.guarded(guard.SPEC_HEALTH)
    def broken():
        return ["ez", "da", "dict"]

    assert broken() == {"error": "blocked_by_guard"}


def test_guard_cannot_be_disabled_by_env(monkeypatch):
    for k in ("GUARD", "GUARD_DISABLED", "MCP_GUARD", "DEBUG"):
        monkeypatch.setenv(k, "0")
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"status": "ok", "model_loaded": True, "x": SECRET}))
    assert server.model_health() == {"status": "ok", "model_loaded": True}


def test_oversized_lists_are_capped(monkeypatch):
    hits = [{"machine_id": f"M{i}", "failure_probability": 0.6, "alert_level": "KONTUZ"} for i in range(900)]
    _mock(monkeypatch, lambda req: httpx.Response(200, json={"hits": {"hits": [{"_source": h} for h in hits]}}))
    out = server.list_active_alerts()
    assert len(out["alerts"]) <= guard.MAX_ITEMS
