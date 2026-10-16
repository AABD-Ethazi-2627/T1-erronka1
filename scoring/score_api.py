"""
CNC Guard — Scoring API
FastAPI mikrozerbitzu bat: sentsore-irakurketa bat jasotzen du eta
entrenatutako ereduaren bidez hutsegite-probabilitatea itzultzen du.

Helburua: NiFi-k InvokeHTTP bidez deitzen dio fase 3an.

Autentifikazioa (OAuth2 estiloko JWT):
  - POST /auth/token  grant_type=password      -> refresh_token + access_token
  - POST /auth/token  grant_type=refresh_token -> access_token berria (5 min)
                                                 + refresh_token berria (errotazioa)
  - /predict-ek "Authorization: Bearer <access_token>" eskatzen du.
"""

import os
import time
import secrets
import logging
from contextlib import asynccontextmanager
from typing import Optional

import joblib
import jwt
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SCORING] %(message)s")
log = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "/models/cnc_failure_model.pkl")

# Ereduak espero dituen sarrera-zutabeak (ai4i2020_train.csv-ko izen berberak)
FEATURES = ["machine_type", "air_temp_K", "process_temp_K", "rpm", "torque_Nm", "tool_wear_min"]

# ── Autentifikazio-konfigurazioa ──────────────────────────────────────────────
JWT_ALG = "HS256"
JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    # Gakorik gabe ausazko bat sortzen da: berrabiaraztean token guztiak baliogabetzen dira
    JWT_SECRET = secrets.token_urlsafe(48)
    log.warning("JWT_SECRET ez dago definituta: ausazko gako bat erabiltzen da")

API_USERNAME = os.getenv("API_USERNAME", "nifi")
API_PASSWORD = os.getenv("API_PASSWORD", "")
ACCESS_TOKEN_EXPIRE_S = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "300"))        # 5 min
REFRESH_TOKEN_EXPIRE_S = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")) * 86400   # 30 egun

# Modeloa aplikazio-abieran behin kargatzen da (ez eskaera bakoitzean)
model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            log.info("Eredua kargatuta: %s", MODEL_PATH)
        except Exception as e:
            log.error("Ezin izan da eredua kargatu (%s): %s", MODEL_PATH, e)
    else:
        # Ez dugu zerbitzua eroriko: /health-ek model_loaded=false erakutsiko du
        log.warning("Ez da eredurik aurkitu hemen: %s", MODEL_PATH)
    yield
    model = None


app = FastAPI(
    title="CNC Guard Scoring API",
    description="Predictive maintenance — hutsegite-probabilitate prediktorea",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Eskema ────────────────────────────────────────────────────────────────────

class SentsoreSaria(BaseModel):
    timestamp: Optional[str] = None
    machine_id: str
    machine_type: str         # "L" | "M" | "H"
    air_temp_K: float
    process_temp_K: float
    rpm: float
    torque_Nm: float
    tool_wear_min: float


class Predikzioa(BaseModel):
    machine_id: str
    failure_predicted: bool
    failure_probability: float
    alert_level: str          # "OK" | "KONTUZ" | "LARRIA"


def alerta_maila(prob: float) -> str:
    if prob > 0.8:
        return "LARRIA"
    if prob >= 0.5:
        return "KONTUZ"
    return "OK"


# ── Tokenak ───────────────────────────────────────────────────────────────────

def sortu_tokena(sub: str, mota: str, iraupena_s: int) -> str:
    orain = int(time.time())
    payload = {
        "sub": sub,
        "type": mota,
        "iat": orain,
        "exp": orain + iraupena_s,
        "jti": secrets.token_urlsafe(12),  # token bakoitza bakarra izan dadin
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def deskodetu_tokena(token: str, mota: str) -> dict:
    """Tokena egiaztatu (sinadura, iraungitzea eta mota). Errorean ValueError."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise ValueError("Tokena iraungita dago")
    except jwt.InvalidTokenError:
        raise ValueError("Token baliogabea")
    if payload.get("type") != mota:
        raise ValueError(f"Token mota okerra ({mota} espero zen)")
    return payload


def oauth_errorea(errorea: str, deskribapena: str, kodea: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=kodea,
        content={"error": errorea, "error_description": deskribapena},
        headers={"Cache-Control": "no-store"},
    )


bearer = HTTPBearer(auto_error=False)


def access_tokena_behar(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    """/predict bezalako endpoint babestuetarako dependentzia."""
    erantzun_goiburuak = {"WWW-Authenticate": "Bearer"}
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer tokena falta da", erantzun_goiburuak)
    try:
        return deskodetu_tokena(cred.credentials, "access")
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e), erantzun_goiburuak)


# ── Endpointak ────────────────────────────────────────────────────────────────

@app.post("/auth/token", tags=["auth"])
async def token(request: Request):
    """
    OAuth2 token endpoint-a (form-urlencoded edo JSON onartzen ditu).

    - grant_type=password&username=..&password=..  -> refresh_token + access_token
    - grant_type=refresh_token&refresh_token=..     -> access_token berria
    """
    if request.headers.get("content-type", "").startswith("application/json"):
        datuak = await request.json()
    else:
        datuak = dict(await request.form())

    grant_type = datuak.get("grant_type")
    orain = int(time.time())

    if grant_type == "password":
        if not API_PASSWORD:
            return oauth_errorea("invalid_grant", "API_PASSWORD ez dago konfiguratuta zerbitzarian")
        user_ok = secrets.compare_digest(str(datuak.get("username", "")), API_USERNAME)
        pass_ok = secrets.compare_digest(str(datuak.get("password", "")), API_PASSWORD)
        if not (user_ok and pass_ok):
            return oauth_errorea("invalid_grant", "Erabiltzaile edo pasahitz okerra")
        sub = API_USERNAME

    elif grant_type == "refresh_token":
        try:
            payload = deskodetu_tokena(str(datuak.get("refresh_token", "")), "refresh")
        except ValueError as e:
            return oauth_errorea("invalid_grant", str(e))
        sub = payload["sub"]

    else:
        return oauth_errorea("unsupported_grant_type", "grant_type: 'password' edo 'refresh_token'")

    # Errotazioa: eskaera bakoitzean refresh token berria (beste REFRESH_TOKEN_EXPIRE_DAYS).
    # Aurrekoak ez dira baliogabetzen (stateless): bakoitza bere iraungitzera arte balio du,
    # horrela NiFi berrabiarazteak ez du ezer apurtzen.
    refresh_token = sortu_tokena(sub, "refresh", REFRESH_TOKEN_EXPIRE_S)

    log.info("Tokenak sortuta (%s, grant=%s)", sub, grant_type)
    return JSONResponse(
        content={
            "access_token": sortu_tokena(sub, "access", ACCESS_TOKEN_EXPIRE_S),
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_S,
            # Refresh token berria: bezeroak gorde eta hurrengo berritzean erabili behar du
            "refresh_token": refresh_token,
            "refresh_expires_in": REFRESH_TOKEN_EXPIRE_S,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None, "model_path": MODEL_PATH}


@app.post("/predict", response_model=Predikzioa)
def predict(saria: SentsoreSaria, _token: dict = Depends(access_tokena_behar)):
    if model is None:
        raise HTTPException(status_code=503, detail=f"Eredua ez dago kargatuta ({MODEL_PATH})")

    X = pd.DataFrame([saria.model_dump(include=set(FEATURES))])[FEATURES]
    try:
        prob = float(model.predict_proba(X)[0][1])
    except Exception as e:
        log.exception("Iragarpen-errorea")
        raise HTTPException(status_code=500, detail=f"Iragarpen-errorea: {e}")

    return Predikzioa(
        machine_id=saria.machine_id,
        failure_predicted=prob >= 0.5,
        failure_probability=round(prob, 4),
        alert_level=alerta_maila(prob),
    )
