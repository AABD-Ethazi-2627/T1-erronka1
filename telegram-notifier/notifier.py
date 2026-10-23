"""Servicio independiente: envía a Telegram las alertas nuevas (KONTUZ / LARRIA) de Elasticsearch."""
import json
import os
import time

import requests

ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200").rstrip("/")
ES_INDEX = os.getenv("ES_INDEX", "cnc-predictions")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
INTERVAL = int(os.getenv("POLL_SECONDS", "15"))
STATE_FILE = os.getenv("STATE_FILE", "/state/seen.json")
MAX_SEEN = 5000
NIVELES = {"LARRIA": "CRÍTICA", "KONTUZ": "ADVERTENCIA"}


def log(msg: str) -> None:
    print(msg, flush=True)


def cargar_estado():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def guardar_estado(seen: list) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(seen[-MAX_SEEN:], f)


def buscar_alertas() -> list:
    body = {
        "size": 500,
        "sort": [{"timestamp": "desc"}],
        "query": {"bool": {"filter": [{"terms": {"alert_level.keyword": list(NIVELES)}}]}},
        "_source": ["timestamp", "machine_id", "failure_probability", "alert_level"],
    }
    r = requests.post(f"{ES_URL}/{ES_INDEX}/_search", json=body, timeout=10)
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()["hits"]["hits"]


def enviar(hit: dict) -> bool:
    s = hit["_source"]
    try:
        prob = f"{float(s.get('failure_probability', 0)):.1%}"
    except (TypeError, ValueError):
        prob = "N/D"
    texto = (
        f"🚨 CNC Guard · {NIVELES.get(s.get('alert_level'), s.get('alert_level'))}\n"
        f"Máquina: {s.get('machine_id', 'N/D')}\n"
        f"Probabilidad de fallo: {prob}\n"
        f"Fecha: {s.get('timestamp', 'N/D')}"
    )
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": texto},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log(f"Error enviando a Telegram: {type(e).__name__}")
        return False


def main() -> None:
    if not TOKEN or not CHAT_ID:
        log("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID no configurados; el servicio queda inactivo.")
        while True:
            time.sleep(3600)

    seen = cargar_estado()
    primera_vez = seen is None
    seen = seen or []
    seen_set = set(seen)
    log(f"Notifier iniciado (cada {INTERVAL}s, índice {ES_INDEX}).")

    while True:
        try:
            hits = buscar_alertas()
            if primera_vez:
                # Línea base: las alertas que ya existen no se envían, solo las futuras.
                for h in hits:
                    seen.append(h["_id"]); seen_set.add(h["_id"])
                guardar_estado(seen)
                primera_vez = False
                log(f"Línea base: {len(hits)} alertas existentes ignoradas.")
            else:
                nuevas = [h for h in hits if h["_id"] not in seen_set]
                for h in reversed(nuevas):  # de más antigua a más reciente
                    if enviar(h):
                        seen.append(h["_id"]); seen_set.add(h["_id"])
                        time.sleep(0.5)  # límite de Telegram: ~1 msg/s por chat
                if nuevas:
                    guardar_estado(seen)
                    seen = seen[-MAX_SEEN:]
                    seen_set = set(seen)
        except requests.RequestException as e:
            log(f"Elasticsearch no disponible: {type(e).__name__}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
