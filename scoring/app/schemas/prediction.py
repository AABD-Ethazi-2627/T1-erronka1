"""
/predict-en sarrera eta irteera eskemak.

Datuak NiFi-n garbitzen dira (ConvertRecord + eskema); hemen datu-motak soilik
egiaztatzen dira. Formatu okerreko eskaerak 422 jasotzen du.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class SentsoreSaria(BaseModel):
    timestamp: Optional[str] = None
    machine_id: str
    machine_type: Literal["L", "M", "H"]
    air_temp_K: float
    process_temp_K: float
    rpm: float
    torque_Nm: float
    tool_wear_min: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-04-29T10:57:50Z",
                "machine_id": "CNC-039",
                "machine_type": "L",
                "air_temp_K": 299.0,
                "process_temp_K": 308.6,
                "rpm": 1587,
                "torque_Nm": 38.6,
                "tool_wear_min": 124,
            }
        }
    }


class Predikzioa(BaseModel):
    # timestamp itzultzen da NiFi-k Elasticsearch-era bidaltzen duen dokumentuak
    # data izan dezan (Kibana-ko denbora-grafikoetarako)
    timestamp: Optional[str] = None
    machine_id: str
    failure_predicted: bool
    failure_probability: float
    alert_level: Literal["OK", "KONTUZ", "LARRIA"]
