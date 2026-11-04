"""
CNC Guard — MCP zerbitzaria.
Scoring API-a eta Elasticsearch Claude-ri tresna gisa erakusten dizkio (stdio bidez).
Irakurketa/kalkulu tresnak soilik: ez du ezer aldatzen ez ezabatzen.
Tresna guztien irteera `guard.py` arnesetik pasatzen da (zerrenda zuria + sekretuen ezkutatzea):
modeloak ez du inoiz kredentzialik, tokenik, IPrik edo akats-testu gordinik jasotzen.

Abiarazteko: python mcp-server/server.py   (normalean .mcp.json-ek abiarazten du)
"""

import os
import sys
import time
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

import guard

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """.env sinplea (KEY=VALUE, '#' iruzkinak). Ingurune-aldagaiek lehentasuna dute."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


_load_dotenv(ROOT / ".env")

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ES_URL = os.getenv("ES_URL", "http://localhost:9200").rstrip("/")
ES_INDEX = os.getenv("ES_INDEX", "cnc-predictions")
API_USERNAME = os.getenv("API_USERNAME", "nifi")
API_PASSWORD = os.getenv("API_PASSWORD", "")
TIMEOUT = 10
ALERT_LEVELS = ("KONTUZ", "LARRIA")

mcp = FastMCP("cnc-guard")

_token = {"value": None, "expires": 0.0}


def _access_token() -> str:
    """JWT access tokena lortu eta cachean gorde (iraungi aurretik berritzen da)."""
    if _token["value"] and time.time() < _token["expires"] - 30:
        return _token["value"]
    if not API_PASSWORD:
        raise RuntimeError("API_PASSWORD ez dago definituta (.env)")
    r = httpx.post(
        f"{API_URL}/auth/token",
        data={"grant_type": "password", "username": API_USERNAME, "password": API_PASSWORD},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    _token["value"] = body["access_token"]
    _token["expires"] = time.time() + body["expires_in"]
    return _token["value"]


def _es_search(body: dict) -> list[dict]:
    r = httpx.post(f"{ES_URL}/{ES_INDEX}/_search", json=body, timeout=TIMEOUT)
    if r.status_code == 404:  # indizea oraindik ez da existitzen: oraindik daturik ez
        return []
    r.raise_for_status()
    return [h["_source"] for h in r.json()["hits"]["hits"]]


@mcp.tool()
@guard.guarded(guard.SPEC_HEALTH)
def model_health() -> dict:
    """Scoring API-aren eta ereduaren egoera (API erantzuten du? eredua kargatuta dago?)."""
    try:
        r = httpx.get(f"{API_URL}/health", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError:
        return {"status": "down"}


@mcp.tool()
@guard.guarded(guard.SPEC_PREDICT)
def predict_failure(
    machine_id: str,
    machine_type: str,
    air_temp_K: float,
    process_temp_K: float,
    rpm: float,
    torque_Nm: float,
    tool_wear_min: float,
) -> dict:
    """Sentsore-irakurketa batetik hutsegite-probabilitatea kalkulatu.

    machine_type: 'L', 'M' edo 'H'. Itzulera: failure_probability (0-1),
    failure_predicted (>0.15) eta alert_level (OK <=0.15, KONTUZ <=0.8, LARRIA >0.8).
    Ez du ezer gordetzen Elasticsearch-en.
    """
    if machine_type not in ("L", "M", "H"):
        return {"error": "machine_type 'L', 'M' edo 'H' izan behar da"}
    if not guard.valid_machine_id(machine_id):
        return {"error": "machine_id baliogabea (letrak, zenbakiak, - eta _; gehienez 32)"}
    if not guard.finite(air_temp_K, process_temp_K, rpm, torque_Nm, tool_wear_min):
        return {"error": "sentsore-balioak zenbaki finituak izan behar dira"}
    payload = {
        "machine_id": machine_id,
        "machine_type": machine_type,
        "air_temp_K": air_temp_K,
        "process_temp_K": process_temp_K,
        "rpm": rpm,
        "torque_Nm": torque_Nm,
        "tool_wear_min": tool_wear_min,
    }
    r = httpx.post(
        f"{API_URL}/predict",
        json=payload,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


@mcp.tool()
@guard.guarded(guard.SPEC_STATUS)
def get_machine_status(machine_id: str, last_n: int = 10) -> dict:
    """Makina baten azken N iragarpenak (berrienetik zaharrenera) Elasticsearch-etik.

    Itzultzen du: iragarpenen zerrenda, probabilitate-joera (trend) eta azken alerta-maila.
    """
    if not guard.valid_machine_id(machine_id):
        return {"error": "machine_id baliogabea (letrak, zenbakiak, - eta _; gehienez 32)"}
    last_n = max(1, min(last_n, 100))
    hits = _es_search(
        {
            "size": last_n,
            "sort": [{"timestamp": "desc"}],
            "query": {"term": {"machine_id.keyword": machine_id}},
            "_source": ["timestamp", "machine_id", "failure_probability", "alert_level"],
        }
    )
    if not hits:
        return {"machine_id": machine_id, "found": False, "predictions": []}

    probs = [float(h.get("failure_probability", 0)) for h in hits]
    delta = probs[0] - probs[-1]  # berriena - zaharrena
    trend = "rising" if delta > 0.05 else "falling" if delta < -0.05 else "stable"
    return {
        "machine_id": machine_id,
        "found": True,
        "latest_alert_level": hits[0].get("alert_level"),
        "trend": trend,
        "probability_delta": round(delta, 4),
        "predictions": hits,
    }


@mcp.tool()
@guard.guarded(guard.SPEC_ALERTS)
def list_active_alerts(minutes: int = 15, min_level: str = "KONTUZ") -> dict:
    """Azken N minutuetan alerta izan duten makinak (makinako azken alerta bakarrik).

    min_level: 'KONTUZ' (KONTUZ + LARRIA) edo 'LARRIA' (kritikoak soilik).
    """
    minutes = max(1, min(minutes, 1440))
    levels = ["LARRIA"] if min_level.upper() == "LARRIA" else list(ALERT_LEVELS)
    hits = _es_search(
        {
            "size": 500,
            "sort": [{"timestamp": "desc"}],
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"alert_level.keyword": levels}},
                        {"range": {"timestamp": {"gte": f"now-{minutes}m"}}},
                    ]
                }
            },
            "_source": ["timestamp", "machine_id", "failure_probability", "alert_level"],
        }
    )

    latest = {}
    for h in hits:  # berrienetik hasita: makinako lehenengoa da berriena
        latest.setdefault(h.get("machine_id"), h)
    alerts = sorted(latest.values(), key=lambda h: -float(h.get("failure_probability", 0)))
    return {"window_minutes": minutes, "count": len(alerts), "alerts": alerts}


if __name__ == "__main__":
    print("CNC Guard MCP zerbitzaria abiarazten (stdio)", file=sys.stderr)
    mcp.run()
