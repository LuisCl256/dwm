"""Clients: datos personales y autenticación por contraseña Argon2id."""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import re
from typing import Annotated
from uuid import uuid4

from argon2 import PasswordHasher, exceptions as argon_errors
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.common import mongo_db, permit, principal, require_internal, strip_mongo

hasher = PasswordHasher()


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    telefono: str | None = Field(default=None, max_length=40)

    @field_validator("telefono")
    @classmethod
    def validate_phone(cls, value):
        if value and not re.fullmatch(r"(?:\+?56\s?)?9\s?\d{4}\s?\d{4}", value.strip()):
            raise ValueError("Teléfono celular chileno inválido")
        return value


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=40)
    direcciones: list[Annotated[str, Field(min_length=6, max_length=300)]] | None = Field(default=None, max_length=10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_db().clients.create_index("email", unique=True)
    mongo_db().clients.create_index("id", unique=True)
    yield


app = FastAPI(title="Flor & Vida | Clients (privado)", lifespan=lifespan)


@app.get("/health")
def health():
    mongo_db().command("ping")
    return {"status": "ok", "service": "clients"}


@app.post("/internal/register", status_code=201, dependencies=[Depends(require_internal)])
def register(body: Registration):
    client = {
        "id": str(uuid4()), "email": str(body.email).lower(), "nombre": body.nombre.strip(),
        "password_hash": hasher.hash(body.password), "telefono": body.telefono,
        "role": "client", "activo": True, "direcciones": [],
        "creado_en": datetime.now(timezone.utc),
    }
    try:
        mongo_db().clients.insert_one(client)
    except DuplicateKeyError:
        raise HTTPException(409, "Correo ya registrado")
    return strip_mongo(client)


@app.post("/internal/login", dependencies=[Depends(require_internal)])
def login(body: Login):
    # No revelar si existe la cuenta; limita la enumeración de correos.
    user = mongo_db().clients.find_one({"email": str(body.email).lower(), "activo": True})
    if user is None:
        raise HTTPException(401, "Credenciales incorrectas")
    try:
        hasher.verify(user["password_hash"], body.password)
    except (argon_errors.VerifyMismatchError, argon_errors.InvalidHashError, argon_errors.VerificationError):
        raise HTTPException(401, "Credenciales incorrectas")
    return {"id": user["id"], "role": user["role"], "nombre": user["nombre"]}


@app.get("/clients/me")
def me(user: Annotated[dict, Depends(principal)]):
    doc = mongo_db().clients.find_one({"id": user["sub"], "activo": True})
    if doc is None:
        raise HTTPException(404, "Cliente inexistente o inactivo")
    return strip_mongo(doc)


@app.patch("/clients/me")
def update_me(data: ProfilePatch, user: Annotated[dict, Depends(principal)]):
    updates = data.model_dump(exclude_unset=True)
    if not updates or any(value is None for key, value in updates.items() if key != "telefono"):
        raise HTTPException(422, "Datos inválidos")
    doc = mongo_db().clients.find_one_and_update(
        {"id": user["sub"], "activo": True}, {"$set": updates},
        return_document=ReturnDocument.AFTER)
    if doc is None:
        raise HTTPException(404, "Cliente inexistente")
    return strip_mongo(doc)


@app.get("/clients")
def clients(user: Annotated[dict, Depends(permit("admin"))], limit: int = 50):
    limit = max(1, min(limit, 100))
    return [strip_mongo(doc) for doc in mongo_db().clients.find().limit(limit)]


@app.get("/clients/{client_id}")
def get_client(client_id: str, user: Annotated[dict, Depends(principal)]):
    if user["role"] != "admin" and user["sub"] != client_id:
        raise HTTPException(403, "No puedes acceder a otro cliente")
    doc = mongo_db().clients.find_one({"id": client_id})
    if doc is None:
        raise HTTPException(404, "Cliente no encontrado")
    return strip_mongo(doc)


@app.delete("/clients/{client_id}")
def deactivate_client(client_id: str, user: Annotated[dict, Depends(permit("admin"))]):
    result = mongo_db().clients.update_one({"id": client_id}, {"$set": {"activo": False}})
    if not result.matched_count:
        raise HTTPException(404, "Cliente no encontrado")
    return {"desactivado": True}
