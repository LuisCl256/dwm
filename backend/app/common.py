"""Utilidades compartidas por procesos privados; cada servicio mantiene su base."""
from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo import MongoClient

ISSUER = "flor-vida-gateway"
AUDIENCE = "flor-vida-api"
_bearer = HTTPBearer(auto_error=False)


def secret(name: str) -> str:
    path = Path(os.getenv("SECRETS_DIR", "/run/secrets")) / name
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"Secreto vacío: {name}")
    return value


@lru_cache

def public_key() -> str:
    return (Path(os.getenv("SECRETS_DIR", "/run/secrets")) / "jwt_public.pem").read_text()


@lru_cache

def private_key() -> str:
    return (Path(os.getenv("SECRETS_DIR", "/run/secrets")) / "jwt_private.pem").read_text()


def issue_token(subject: str, role: str, *, expiry_minutes: int = 30) -> str:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": subject,
        "role": role,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=expiry_minutes),
    }, private_key(), algorithm="RS256")


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, public_key(), algorithms=["RS256"],
                             issuer=ISSUER, audience=AUDIENCE,
                             options={"require": ["exp", "sub", "role", "iss", "aud"]})
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o vencido")
    if payload.get("role") not in {"client", "employee", "admin"}:
        raise HTTPException(status_code=403, detail="Rol inválido")
    return payload


def principal(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token requerido")
    return decode_token(credentials.credentials)


def permit(*roles: str) -> Callable:
    def require(user: Annotated[dict, Depends(principal)]) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user
    return require


def require_internal(x_internal_secret: Annotated[str | None, Header()] = None) -> None:
    import secrets
    if not x_internal_secret or not secrets.compare_digest(x_internal_secret, secret("service_token")):
        raise HTTPException(status_code=403, detail="Acceso de servicio denegado")


@lru_cache

def mongo_db():
    from urllib.parse import quote_plus
    dbname = os.environ["MONGO_DB"]
    username = os.environ["MONGO_USER"]
    password = secret(f"mongo-{os.environ['MONGO_SERVICE']}-password")
    host = os.getenv("MONGO_HOST", "mongo")
    uri = f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:27017/{dbname}?authSource={dbname}"
    return MongoClient(uri, serverSelectionTimeoutMS=6000)[dbname]


def strip_mongo(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    result = dict(doc)
    result.pop("_id", None)
    result.pop("password_hash", None)
    result.pop("_outbox", None)  # eventos internos jamás aparecen en REST/GraphQL
    return result
