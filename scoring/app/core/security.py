"""JWT tokenak (access + refresh) eta endpoint babestuetarako dependentzia."""

import secrets
import time
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings


def sortu_tokena(sub: str, mota: str, iraupena_s: int) -> str:
    orain = int(time.time())
    payload = {
        "sub": sub,
        "type": mota,
        "iat": orain,
        "exp": orain + iraupena_s,
        "jti": secrets.token_urlsafe(12),  # token bakoitza bakarra izan dadin
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def deskodetu_tokena(token: str, mota: str) -> dict:
    """Tokena egiaztatu (sinadura, iraungitzea eta mota). Errorean ValueError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.ExpiredSignatureError:
        raise ValueError("Tokena iraungita dago")
    except jwt.InvalidTokenError:
        raise ValueError("Token baliogabea")
    if payload.get("type") != mota:
        raise ValueError(f"Token mota okerra ({mota} espero zen)")
    return payload


def egiaztatu_kredentzialak(username: str, password: str) -> bool:
    if not settings.api_password:
        return False
    # Biak beti konparatu (compare_digest): denbora-erasoak saihesteko
    user_ok = secrets.compare_digest(username, settings.api_username)
    pass_ok = secrets.compare_digest(password, settings.api_password)
    return user_ok and pass_ok


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
