"""
CNC Guard — Scoring API
FastAPI mikrozerbitzu bat: sentsore-irakurketa bat jasotzen du eta
entrenatutako ereduaren bidez hutsegite-probabilitatea itzultzen du.

Helburua: NiFi-k InvokeHTTP bidez deitzen dio fase 3an.
"""

import os
import logging
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SCORING] %(message)s")
log = logging.getLogger(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "/models/cnc_failure_model.pkl")

# Modeloa aplikazio-abieran behin kargatzen da (ez eskaera bakoitzean)
model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    ### Kodea hemen ###


app = FastAPI(
    title="CNC Guard Scoring API",
    description="Predictive maintenance — hutsegite-probabilitate prediktorea",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Eskema ────────────────────────────────────────────────────────────────────

class SentsoreSaria(BaseModel):
    ### Kodea hemen ###


class Predikzioa(BaseModel):
    ### Kodea hemen ###
    alert_level: str          # "OK" | "KONTUZ" | "LARRIA"


# ── Endpointak ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    ### Kodea hemen ###


@app.post("/predict", response_model=Predikzioa)
def predict(saria: SentsoreSaria):
    ### Kodea hemen ###

