"""Ereduaren karga (abieran behin) eta iragarpena."""

import logging
import os

import joblib
import pandas as pd

from cnc_ml.columns import RAW_FEATURES

log = logging.getLogger(__name__)

# Alerta-mailen mugak: OK <= %50 < KONTUZ <= %80 < LARRIA
FAILURE_THRESHOLD = 0.5
LARRIA_THRESHOLD = 0.8


class ModelService:
    def __init__(self):
        self.model = None
        self.path = None

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def load(self, path: str) -> None:
        self.path = path
        if not os.path.exists(path):
            # Ez dugu zerbitzua eroriko: /health-ek model_loaded=false erakutsiko du
            log.warning("Ez da eredurik aurkitu hemen: %s", path)
            return
        try:
            self.model = joblib.load(path)
            log.info("Eredua kargatuta: %s", path)
        except Exception as e:
            log.error("Ezin izan da eredua kargatu (%s): %s", path, e)

    def unload(self) -> None:
        self.model = None

    def predict_proba(self, saria: dict) -> float:
        """Hutsegite-probabilitatea. .pkl-ak Pipeline osoa da: sarrera gordinak nahikoa."""
        X = pd.DataFrame([{k: saria[k] for k in RAW_FEATURES}])[RAW_FEATURES]
        return float(self.model.predict_proba(X)[0][1])


def alerta_maila(prob: float) -> str:
    if prob > LARRIA_THRESHOLD:
        return "LARRIA"
    if prob > FAILURE_THRESHOLD:
        return "KONTUZ"
    return "OK"


model_service = ModelService()
