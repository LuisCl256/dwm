import os
import secrets
from datetime import datetime, timedelta
from typing import Dict

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel

load_dotenv()

AUTH_INTROSPECTION_SECRET = os.getenv("AUTH_INTROSPECTION_SECRET")
if not AUTH_INTROSPECTION_SECRET:
    raise RuntimeError("AUTH_INTROSPECTION_SECRET no está configurado")

SESSION_TTL_SECONDS = 900  # 15 minutos

app = FastAPI(
    title="Flor & Vida — Auth Service",
    description="Login, introspección y logout para el personal.",
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Personal simulado

USERS = {
    "valentina": {
        "user_id": "USR-001",
        "password_hash": pwd_context.hash("staff123"),
        "roles": ["staff"],
    },
    "camila": {
        "user_id": "USR-002",
        "password_hash": pwd_context.hash("admin123"),
        "roles": ["staff", "admin"],
    },
}

# token de sesión -> datos de la sesión (en memoria, se pierde al reiniciar)
SESSIONS: Dict[str, dict] = {}


# Esquemas

class LoginIn(BaseModel):
    username: str
    password: str


class IntrospectIn(BaseModel):
    token: str


# Solo el Gateway puede llamar a /introspect y /logout
def verify_gateway(x_introspection_secret: str = Header(default="")):
    valido = secrets.compare_digest(x_introspection_secret,
                                    AUTH_INTROSPECTION_SECRET)
    if not valido:
        raise HTTPException(status_code=403,
                            detail="Solicitud no autorizada desde Gateway")


# Endpoints

@app.get("/health")
def health():
    return {"status": "OK", "service": "Flor & Vida — Auth Service"}


@app.post("/login")
def login(datos: LoginIn):
    usuario = USERS.get(datos.username)
    credenciales_validas = usuario is not None and pwd_context.verify(
        datos.password, usuario["password_hash"]
    )
    if not credenciales_validas:
        raise HTTPException(status_code=401,
                            detail="Usuario o contraseña incorrectos")

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "user_id": usuario["user_id"],
        "username": datos.username,
        "roles": usuario["roles"],
        "expires_at": datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS),
    }
    return {"access_token": token, "token_type": "bearer",
            "expires_in": SESSION_TTL_SECONDS}


@app.post("/introspect", dependencies=[Depends(verify_gateway)])
def introspect(datos: IntrospectIn):
    sesion = SESSIONS.get(datos.token)
    if not sesion or sesion["expires_at"] < datetime.utcnow():
        return {"active": False}
    return {
        "active": True,
        "user_id": sesion["user_id"],
        "username": sesion["username"],
        "roles": sesion["roles"],
    }


@app.post("/logout", dependencies=[Depends(verify_gateway)])
def logout(datos: IntrospectIn):
    SESSIONS.pop(datos.token, None)
    return {"status": "ok"}
