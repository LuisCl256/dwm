"""Orders: pedido con detalle 1:N, reserva stock y autorización de propietarios."""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
import os
import re
from typing import Annotated, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pymongo import ReturnDocument

from app.common import mongo_db, principal, require_internal, secret, strip_mongo
from app.events import order_event

INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory:8000")
TRANSITIONS = {
    "recibido": {"preparando", "cancelado"},
    "preparando": {"despachado", "cancelado"},
    "despachado": {"entregado"},
    "entregado": set(),
    "cancelado": set(),
}


def internal_headers():
    return {"X-Internal-Secret": secret("service_token")}


def call_inventory(method: str, url: str, *, data=None):
    try:
        with httpx.Client(timeout=8) as client:
            res = client.request(method, INVENTORY_URL + url, headers=internal_headers(), json=data)
    except httpx.RequestError:
        raise HTTPException(502, "Inventory no está disponible")
    if res.status_code >= 400:
        raise HTTPException(res.status_code if 400 <= res.status_code < 500 else 502,
                            f"Inventory rechazó la operación: {res.text[:300]}")
    return res.json()


class OrderItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=3, max_length=120)
    email: EmailStr
    telefono: str = Field(min_length=8, max_length=40)
    items: list[OrderItemIn] = Field(min_length=1, max_length=20)
    fecha: date
    direccion: str = Field(min_length=6, max_length=300)
    mensaje: str | None = Field(default=None, max_length=500)

    @field_validator("telefono")
    @classmethod
    def validate_phone(cls, value):
        if not re.fullmatch(r"(?:\+?56\s?)?9\s?\d{4}\s?\d{4}", value.strip()):
            raise ValueError("Teléfono celular chileno inválido")
        return value

    @field_validator("fecha")
    @classmethod
    def future_delivery(cls, value: date):
        if value < datetime.now(ZoneInfo("America/Santiago")).date():
            raise ValueError("La fecha no puede ser anterior al día actual en Chile")
        return value

    @field_validator("items")
    @classmethod
    def unique_items(cls, value: list[OrderItemIn]):
        ids = [item.product_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("No repetir productos; sumar las cantidades")
        return value


class OrderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: Literal["preparando", "despachado", "entregado", "cancelado"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_db().orders.create_index("numero_pedido", unique=True)
    mongo_db().orders.create_index("client_id")
    yield


app = FastAPI(title="Flor & Vida | Orders (privado)", lifespan=lifespan)


@app.get("/health")
def health():
    mongo_db().command("ping")
    return {"status": "ok", "service": "orders"}


@app.post("/orders", status_code=201)
def create_order(data: OrderCreate, user: Annotated[dict, Depends(principal)]):
    lines = []
    for item in data.items:
        product = call_inventory("GET", f"/internal/products/{item.product_id}")
        lines.append({"product_id": product["id"], "nombre": product["nombre"],
                      "quantity": item.quantity, "precio_unitario": product["precio"],
                      "subtotal": product["precio"] * item.quantity})
    number = f"FV-{datetime.now(timezone.utc).year}-{uuid4().hex[:12].upper()}"
    reservation = {"reservation_id": number, "items": [i.model_dump() for i in data.items]}
    call_inventory("POST", "/internal/reserve", data=reservation)
    document = {**data.model_dump(exclude={"items"}), "fecha": data.fecha.isoformat(),
                "client_id": user["sub"], "numero_pedido": number, "estado": "recibido",
                "items": lines, "total": sum(line["subtotal"] for line in lines),
                "creado_en": datetime.now(timezone.utc)}
    document["_outbox"] = {"event": order_event(number, document["total"], lines)}
    try:
        mongo_db().orders.insert_one(document)
    except Exception:
        # Compensación básica si Mongo rechaza el pedido después de reservar stock.
        try:
            call_inventory("POST", f"/internal/release/{number}")
        except Exception:
            pass  # Requiere conciliación de fallos; documentado en arquitectura.md.
        raise HTTPException(503, "No fue posible almacenar el pedido")
    return strip_mongo(document)


@app.get("/orders")
def list_orders(user: Annotated[dict, Depends(principal)], limit: int = Query(30, ge=1, le=100)):
    filt = {} if user["role"] in {"admin", "employee"} else {"client_id": user["sub"]}
    docs = mongo_db().orders.find(filt).sort("creado_en", -1).limit(limit)
    return [strip_mongo(doc) for doc in docs]


@app.get("/orders/{number}")
def get_order(number: str, user: Annotated[dict, Depends(principal)]):
    doc = mongo_db().orders.find_one({"numero_pedido": number})
    if doc is None:
        raise HTTPException(404, "Pedido no encontrado")
    if user["role"] not in {"admin", "employee"} and doc["client_id"] != user["sub"]:
        raise HTTPException(403, "Este pedido no te pertenece")
    return strip_mongo(doc)


@app.patch("/orders/{number}")
def change_status(number: str, data: OrderStatus, user: Annotated[dict, Depends(principal)]):
    doc = mongo_db().orders.find_one({"numero_pedido": number})
    if doc is None:
        raise HTTPException(404, "Pedido no encontrado")
    owner = doc["client_id"] == user["sub"]
    if user["role"] == "client" and (not owner or data.estado != "cancelado"):
        raise HTTPException(403, "Solo puedes cancelar tus propios pedidos")
    if data.estado not in TRANSITIONS[doc["estado"]]:
        raise HTTPException(409, "Transición de estado inválida")
    # Si hay una modificación concurrente se rechaza, sin sobrescribir otro estado.
    updated = mongo_db().orders.find_one_and_update(
        {"numero_pedido": number, "estado": doc["estado"]},
        {"$set": {"estado": data.estado, "actualizado_en": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER)
    if updated is None:
        raise HTTPException(409, "El pedido fue modificado simultáneamente")
    if data.estado == "cancelado":
        try:
            call_inventory("POST", f"/internal/release/{number}")
        except HTTPException:
            # La cancelación persiste; se requiere reconciliar la reserva si falla Inventory.
            raise HTTPException(503, "Pedido cancelado; liberación de stock pendiente de reconciliación")
    return strip_mongo(updated)


@app.get("/internal/orders/{number}", dependencies=[Depends(require_internal)])
def internal_order(number: str):
    doc = mongo_db().orders.find_one({"numero_pedido": number})
    if doc is None:
        raise HTTPException(404, "Pedido no encontrado")
    # Contrato interno mínimo, sin nombre, correo ni domicilio.
    return {"numero_pedido": doc["numero_pedido"], "client_id": doc["client_id"],
            "total": doc["total"], "estado": doc["estado"]}
