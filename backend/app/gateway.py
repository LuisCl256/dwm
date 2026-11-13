"""ÚNICO puerto HTTP publicado: autenticación JWT y proxy de rutas permitidas."""
from __future__ import annotations
import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.common import decode_token, issue_token, secret

app = FastAPI(title="Flor & Vida | API Gateway", version="1.0.0")

SERVICES = {
    "inventory": ("http://inventory:8000", "products"),
    "orders": ("http://orders:8000", "orders"),
    "clients": ("http://clients:8000", "clients"),
    "payments": ("http://payments:8000", "payments"),
    "analytics": ("http://analytics:8000", "analytics"),
}


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    telefono: str | None = Field(default=None, max_length=40)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


async def call_clients(path: str, data: dict):
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            result = await client.post("http://clients:8000" + path, json=data,
                                       headers={"X-Internal-Secret": secret("service_token")})
    except httpx.RequestError:
        raise HTTPException(502, "Servicio de clientes no disponible")
    # Respuestas propias de Clients sin encabezados internos.
    if result.status_code >= 400:
        try:
            detail = result.json().get("detail", "Solicitud inválida")
        except Exception:
            detail = "Solicitud inválida"
        raise HTTPException(result.status_code if result.status_code < 500 else 502, detail)
    return result.json()


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.post("/auth/register", status_code=201)
async def register(body: RegisterRequest):
    return await call_clients("/internal/register", body.model_dump(mode="json"))


@app.post("/auth/login")
async def login(body: LoginRequest):
    person = await call_clients("/internal/login", body.model_dump(mode="json"))
    token = issue_token(person["id"], person["role"])
    return {"access_token": token, "token_type": "bearer", "expires_in": 1800,
            "role": person["role"]}


@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def route(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(404, "Servicio desconocido")
    base, allowed_root = SERVICES[service]
    segments = path.split("/")
    # No exponer operaciones de servicio /internal, /docs, /health, etc.
    if not path or segments[0] != allowed_root or any(
            s.lower() in {".", "..", "internal"} or not s for s in segments):
        raise HTTPException(404, "Ruta no expuesta por el Gateway")

    public_read = service == "inventory" and request.method == "GET" and allowed_root == segments[0]
    authorization = request.headers.get("authorization", "")
    if authorization:
        pieces = authorization.split(" ", 1)
        if len(pieces) != 2 or pieces[0].lower() != "bearer":
            raise HTTPException(401, "Se requiere Bearer válido")
        decode_token(pieces[1])
    elif not public_read:
        raise HTTPException(401, "Bearer token requerido")

    target = f"{base}/{path}"
    headers = {}
    if authorization:
        headers["Authorization"] = authorization
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            result = await client.request(request.method, target, headers=headers,
                                          content=await request.body(),
                                          params=request.query_params)
    except httpx.RequestError:
        raise HTTPException(502, "Servicio interno no disponible")
    returned_headers = {}
    if result.headers.get("content-type"):
        returned_headers["content-type"] = result.headers["content-type"]
    return Response(content=result.content, status_code=result.status_code,
                    headers=returned_headers)


@app.post("/graphql", include_in_schema=True, tags=["GraphQL"])
async def graphql_proxy(request: Request):
    """Endpoint externo único de GraphQL; el servidor GraphQL permanece privado."""
    body = await request.body()
    if len(body) > 16384:
        raise HTTPException(413, "Consulta GraphQL demasiado grande")
    if "application/json" not in request.headers.get("content-type", ""):
        raise HTTPException(415, "GraphQL requiere application/json")
    authorization = request.headers.get("authorization")
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(401, "Bearer token inválido")
        decode_token(parts[1])
    headers = {"Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            result = await client.post("http://graphql:8000/graphql", content=body, headers=headers)
    except httpx.RequestError:
        raise HTTPException(502, "Gateway GraphQL no disponible")
    return Response(content=result.content, status_code=result.status_code,
                    media_type="application/json")
