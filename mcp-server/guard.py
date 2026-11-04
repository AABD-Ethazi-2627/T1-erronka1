"""
CNC Guard — MCP segurtasun-arnesa.

MCP tresnek itzultzen duten guztia modeloaren testuinguruan sartzen da. Hemendik pasatzen da
beti, eta ez da ezgaitu daitekeen aukerarik (ez ingurune-aldagairik, ez parametrorik):

1. Zerrenda zuria (allowlist): eremu ezagunak eta mota/formatu zehatzekin soilik pasatzen dira;
   gainerako guztia baztertzen da (API/Elasticsearch-ek eremu berriak gehitzen badituzte ere).
2. Akatsak: salbuespenen testua ez da inoiz itzultzen (URLak, goiburuak, bideak eta kredentzialak
   izan ditzake); kode finkoak soilik (`http_401`, `timeout`...).
3. Ezkutatzea (redaction): balio guztietan sekretuen ereduak eta .env-ko sekretuen balio literalak
   `[REDACTED]` bihurtzen dira, zerrenda zuriaren ondoren ere (defentsa sakona).
4. Huts egiten badu, ez du ezer itzultzen (fail closed).

Stderr-era kontagailuak soilik idazten dira, inoiz edukirik ez.
"""

import functools
import math
import os
import re
import sys

REDACTED = "[REDACTED]"
MAX_ITEMS = 500
MAX_OUTPUT_CHARS = 100_000

# .env-ko zein aldagaik dute sekretu/gune sentikorra: haien balio literalak ezkutatzen dira.
_SECRET_ENV_KEY = re.compile(r"(PASS|SECRET|TOKEN|KEY|CREDENTIAL)", re.I)
_EXTRA_SENSITIVE_ENV = ("SMB_IP", "SMB_USERNAME", "NIFI_USERNAME", "TELEGRAM_CHAT_ID")

_PATTERNS = [
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),  # JWT
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),  # Authorization: Bearer ...
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),  # Telegram bot token
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@\S+"),  # URL erabiltzaile:pasahitza@
    re.compile(r"(?i)\b(pass(word)?|passwd|pwd|secret|token|api[_-]?key|credential)s?\s*[=:]\s*\S+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+"),  # posta-helbideak
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),  # IPv4
    re.compile(r"\b[A-Za-z0-9+/_-]{32,}={0,2}"),  # token luze antzekoak (hex/base64)
]

_stats = {"redactions": 0, "dropped": 0}


def secret_values() -> list[str]:
    """Prozesuaren ingurunean (.env barne) dauden sekretuen balio literalak, luzeenak lehenik."""
    vals = {
        v
        for k, v in os.environ.items()
        if ((_SECRET_ENV_KEY.search(k) and "EXPIRE" not in k.upper()) or k in _EXTRA_SENSITIVE_ENV)
        and len(v) >= 4
    }
    return sorted(vals, key=len, reverse=True)


def redact_text(text: str) -> str:
    for secret in secret_values():
        if secret in text:
            text = text.replace(secret, REDACTED)
            _stats["redactions"] += 1
    for pattern in _PATTERNS:
        text, n = pattern.subn(REDACTED, text)
        _stats["redactions"] += n
    return text


# ── Zerrenda zuria: eskemak ──────────────────────────────────────────────────
def _s(regex: str, limit: int = 64):
    return ("str", re.compile(regex), limit)


ID = _s(r"[A-Za-z0-9_-]{1,32}", 32)
TIMESTAMP = _s(r"[0-9T:+.Z -]{10,40}", 40)
LEVEL = ("enum", {"OK", "KONTUZ", "LARRIA"})
TREND = ("enum", {"rising", "falling", "stable"})
STATUS = _s(r"[a-z_]{1,20}", 20)

PREDICTION = {
    "timestamp": TIMESTAMP,
    "machine_id": ID,
    "failure_predicted": bool,
    "failure_probability": float,
    "alert_level": LEVEL,
}
PREDICTION_ITEM = {k: PREDICTION[k] for k in ("timestamp", "machine_id", "failure_probability", "alert_level")}

SPEC_HEALTH = {"status": STATUS, "model_loaded": bool}
SPEC_PREDICT = PREDICTION
SPEC_STATUS = {
    "machine_id": ID,
    "found": bool,
    "latest_alert_level": LEVEL,
    "trend": TREND,
    "probability_delta": float,
    "predictions": [PREDICTION_ITEM],
}
SPEC_ALERTS = {"window_minutes": int, "count": int, "alerts": [PREDICTION_ITEM]}

_MISSING = object()


def project(value, spec):
    """`value`-ren zati baliodunak itzultzen ditu `spec`-en arabera; besteak baztertzen dira."""
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            return _MISSING
        out = {}
        for key, sub in spec.items():
            if key in value:
                got = project(value[key], sub)
                if got is _MISSING:
                    _stats["dropped"] += 1
                else:
                    out[key] = got
        _stats["dropped"] += len(set(value) - set(spec))
        return out
    if isinstance(spec, list):
        if not isinstance(value, list):
            return _MISSING
        items = [project(v, spec[0]) for v in value[:MAX_ITEMS]]
        return [i for i in items if i is not _MISSING]
    if spec is bool:
        return value if isinstance(value, bool) else _MISSING
    if spec in (int, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return _MISSING
        if isinstance(value, float) and not math.isfinite(value):
            return _MISSING
        return spec(value)
    kind = spec[0]
    if kind == "enum":
        return value if isinstance(value, str) and value in spec[1] else _MISSING
    if kind == "str":
        ok = isinstance(value, str) and len(value) <= spec[2] and spec[1].fullmatch(value)
        return value if ok else _MISSING
    return _MISSING


def scrub(value):
    """Egitura osoko string guztiei ezkutatzea aplikatu."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


# ── Sarrera-balidazioa ───────────────────────────────────────────────────────
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,32}")


def valid_machine_id(machine_id) -> bool:
    return isinstance(machine_id, str) and _ID_RE.fullmatch(machine_id) is not None


def finite(*numbers) -> bool:
    return all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) for n in numbers)


# ── Akatsak: kode finkoak soilik ─────────────────────────────────────────────
def safe_error(exc: BaseException) -> str:
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        return f"http_{exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.HTTPError):
        return "service_unreachable"
    if isinstance(exc, RuntimeError):
        return "not_configured"
    return "internal_error"


def guarded(spec):
    """MCP tresna baten irteera zerrenda zuritik eta ezkutatzetik pasatzen du."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _stats.update(redactions=0, dropped=0)
            try:
                try:
                    out = fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 — testua ez da inoiz itzultzen
                    out = {"error": safe_error(exc)}
                if not isinstance(out, dict):
                    raise TypeError("irteera ez da dict bat")
                if "error" in out:  # tresnak berak sortutako mezu finkoak edo safe_error kodeak
                    result = {"error": redact_text(str(out["error"]))[:120]}
                else:
                    result = project(out, spec)
                    if result is _MISSING:
                        raise TypeError("irteerak ez du eskemarik betetzen")
                    result = scrub(result)
                if len(repr(result)) > MAX_OUTPUT_CHARS:
                    raise ValueError("irteera handiegia")
                print(
                    f"guard[{fn.__name__}]: ezkutatuak={_stats['redactions']} baztertuak={_stats['dropped']}",
                    file=sys.stderr,
                )
                return result
            except Exception:  # noqa: BLE001 — fail closed
                print(f"guard[{fn.__name__}]: huts egin du, irteera blokeatuta", file=sys.stderr)
                return {"error": "blocked_by_guard"}

        return wrapper

    return decorator
