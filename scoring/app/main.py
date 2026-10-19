"""
CNC Guard — Scoring API
Sentsore-irakurketa bat jasotzen du eta entrenatutako ereduaren bidez
hutsegite-probabilitatea itzultzen du. NiFi-k InvokeHTTP bidez deitzen dio 3. fasean.

Abiarazteko: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health, predict
from app.config import settings
from app.services.model import model_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SCORING] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eredua abieran behin kargatzen da (ez eskaera bakoitzean)
    model_service.load(settings.model_path)
    yield
    model_service.unload()


app = FastAPI(
    title="CNC Guard Scoring API",
    description="Predictive maintenance — hutsegite-probabilitate prediktorea",
    version="1.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(health.router)
app.include_router(predict.router)
