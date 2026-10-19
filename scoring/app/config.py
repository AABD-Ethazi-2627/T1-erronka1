"""Konfigurazioa ingurune-aldagaietatik (docker-compose.yml edo .env)."""

import logging
import os
import secrets
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    model_path: str
    jwt_secret: str
    jwt_alg: str
    api_username: str
    api_password: str
    access_token_expire_s: int
    refresh_token_expire_s: int


def load_settings() -> Settings:
    jwt_secret = os.getenv("JWT_SECRET", "")
    if not jwt_secret:
        # Gakorik gabe ausazko bat sortzen da: berrabiaraztean token guztiak baliogabetzen dira
        jwt_secret = secrets.token_urlsafe(48)
        log.warning("JWT_SECRET ez dago definituta: ausazko gako bat erabiltzen da")

    return Settings(
        model_path=os.getenv("MODEL_PATH", "/models/cnc_failure_model.pkl"),
        jwt_secret=jwt_secret,
        jwt_alg="HS256",
        api_username=os.getenv("API_USERNAME", "nifi"),
        api_password=os.getenv("API_PASSWORD", ""),
        access_token_expire_s=int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "300")),             # 5 min
        refresh_token_expire_s=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")) * 86400,      # 30 egun
    )


settings = load_settings()
