"""
CNC Guard — Scoring API
FastAPI mikrozerbitzu bat: sentsore-irakurketa bat jasotzen du eta
entrenatutako ereduaren bidez hutsegite-probabilitatea itzultzen du.

Helburua: NiFi-k InvokeHTTP bidez deitzen dio fase 3an.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SCORING] %(message)s")
log = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "/models/cnc_failure_model.pkl")

# Ereduak espero dituen sarrera-zutabeak (ai4i2020_train.csv-ko izen berberak)
FEATURES = ["machine_type", "air_temp_K", "process_temp_K", "rpm", "torque_Nm", "tool_wear_min"]

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


# ── Endpointak ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None, "model_path": MODEL_PATH}


@app.post("/predict", response_model=Predikzioa)
def predict(saria: SentsoreSaria):
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
