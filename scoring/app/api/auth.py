"""
OAuth2 estiloko token endpoint-a:
  - grant_type=password      -> refresh_token + access_token
  - grant_type=refresh_token -> access_token berria (5 min) + refresh_token berria (errotazioa)
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.security import deskodetu_tokena, egiaztatu_kredentzialak, sortu_tokena

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def oauth_errorea(errorea: str, deskribapena: str, kodea: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=kodea,
        content={"error": errorea, "error_description": deskribapena},
        headers={"Cache-Control": "no-store"},
    )


@router.post("/token")
async def token(request: Request):
    """form-urlencoded (NiFi InvokeHTTP) edo JSON onartzen ditu."""
    if request.headers.get("content-type", "").startswith("application/json"):
        datuak = await request.json()
    else:
        datuak = dict(await request.form())

    grant_type = datuak.get("grant_type")

    if grant_type == "password":
        if not settings.api_password:
            return oauth_errorea("invalid_grant", "API_PASSWORD ez dago konfiguratuta zerbitzarian")
        if not egiaztatu_kredentzialak(str(datuak.get("username", "")), str(datuak.get("password", ""))):
            return oauth_errorea("invalid_grant", "Erabiltzaile edo pasahitz okerra")
        sub = settings.api_username

    elif grant_type == "refresh_token":
        try:
            payload = deskodetu_tokena(str(datuak.get("refresh_token", "")), "refresh")
        except ValueError as e:
            return oauth_errorea("invalid_grant", str(e))
        sub = payload["sub"]

    else:
        return oauth_errorea("unsupported_grant_type", "grant_type: 'password' edo 'refresh_token'")

    # Errotazioa: eskaera bakoitzean refresh token berria. Aurrekoak ez dira baliogabetzen
    # (stateless): bakoitza bere iraungitzera arte balio du, NiFi berrabiarazteak ez du ezer apurtzen.
    log.info("Tokenak sortuta (%s, grant=%s)", sub, grant_type)
    return JSONResponse(
        content={
            "access_token": sortu_tokena(sub, "access", settings.access_token_expire_s),
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_s,
            "refresh_token": sortu_tokena(sub, "refresh", settings.refresh_token_expire_s),
            "refresh_expires_in": settings.refresh_token_expire_s,
        },
        headers={"Cache-Control": "no-store"},
    )
