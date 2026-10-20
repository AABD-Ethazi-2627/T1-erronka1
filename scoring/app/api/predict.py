import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import access_tokena_behar
from app.schemas.prediction import Predikzioa, SentsoreSaria
from app.services.model import FAILURE_THRESHOLD, alerta_maila, model_service

log = logging.getLogger(__name__)
router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=Predikzioa)
def predict(saria: SentsoreSaria, _token: dict = Depends(access_tokena_behar)):
    if not model_service.loaded:
        raise HTTPException(status_code=503, detail=f"Eredua ez dago kargatuta ({model_service.path})")

    try:
        prob = model_service.predict_proba(saria.model_dump())
    except Exception as e:
        log.exception("Iragarpen-errorea")
        raise HTTPException(status_code=500, detail=f"Iragarpen-errorea: {e}")

    return Predikzioa(
        timestamp=saria.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        machine_id=saria.machine_id,
        failure_predicted=prob > FAILURE_THRESHOLD,
        failure_probability=round(prob, 4),
        alert_level=alerta_maila(prob),
    )
