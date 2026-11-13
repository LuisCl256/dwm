"""Payments: operaciones SIMULADAS, sin medios de pago ni datos de tarjetas."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from typing import Annotated, Literal
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.common import mongo_db, principal, permit, secret, strip_mongo
from app.events import payment_event

ORDERS_URL = os.getenv("ORDERS_URL", "http://orders:8000")


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero_pedido: str = Field(min_length=5, max_length=80)


class PaymentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: Literal["aprobado", "rechazado"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_db().payments.create_index("id", unique=True)
    mongo_db().payments.create_index("numero_pedido", unique=True)
    yield


app = FastAPI(title="Flor & Vida | Payments (privado; simulación)", lifespan=lifespan)


def order_info(number: str):
    try:
        with httpx.Client(timeout=8) as client:
            result = client.get(f"{ORDERS_URL}/internal/orders/{number}",
                                headers={"X-Internal-Secret": secret("service_token")})
    except httpx.RequestError:
        raise HTTPException(502, "Orders no disponible")
    if result.status_code == 404:
        raise HTTPException(404, "Pedido no encontrado")
    if result.status_code != 200:
        raise HTTPException(502, "No se pudo validar el pedido")
    return result.json()


@app.get("/health")
def health():
    mongo_db().command("ping")
    return {"status": "ok", "service": "payments"}


@app.post("/payments", status_code=201)
def create_payment(data: PaymentCreate, user: Annotated[dict, Depends(principal)]):
    order = order_info(data.numero_pedido)
    if user["role"] not in {"admin", "employee"} and order["client_id"] != user["sub"]:
        raise HTTPException(403, "El pedido no te pertenece")
    if order["estado"] == "cancelado":
        raise HTTPException(409, "No se puede pagar un pedido cancelado")
    doc = {"id": str(uuid4()), "numero_pedido": data.numero_pedido,
           "client_id": order["client_id"], "monto": order["total"], "moneda": "CLP",
           "estado": "pendiente", "metodo": "simulacion",
           "creado_en": datetime.now(timezone.utc)}
    try:
        mongo_db().payments.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "Ya existe un pago para este pedido")
    return strip_mongo(doc)


@app.get("/payments")
def list_payments(user: Annotated[dict, Depends(principal)]):
    filt = {} if user["role"] == "admin" else {"client_id": user["sub"]}
    return [strip_mongo(doc) for doc in mongo_db().payments.find(filt).limit(100)]


@app.get("/payments/by-order/{number}")
def get_payment_by_order(number: str, user: Annotated[dict, Depends(principal)]):
    doc = mongo_db().payments.find_one({"numero_pedido": number})
    if doc is None:
        raise HTTPException(404, "Pago no encontrado")
    if user["role"] != "admin" and doc["client_id"] != user["sub"]:
        raise HTTPException(403, "El pago no te pertenece")
    return strip_mongo(doc)


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str, user: Annotated[dict, Depends(principal)]):
    doc = mongo_db().payments.find_one({"id": payment_id})
    if doc is None:
        raise HTTPException(404, "Pago no encontrado")
    if user["role"] != "admin" and user["sub"] != doc["client_id"]:
        raise HTTPException(403, "El pago no te pertenece")
    return strip_mongo(doc)


@app.patch("/payments/{payment_id}")
def change_payment_status(payment_id: str, data: PaymentStatus,
                          user: Annotated[dict, Depends(permit("admin"))]):
    current = mongo_db().payments.find_one({"id": payment_id, "estado": "pendiente"})
    if current is None:
        raise HTTPException(409, "Pago no encontrado o ya procesado")
    updates = {"estado": data.estado, "procesado_en": datetime.now(timezone.utc)}
    if data.estado == "aprobado":
        updates["_outbox"] = {"event": payment_event(current["numero_pedido"], current["monto"])}
    doc = mongo_db().payments.find_one_and_update(
        {"id": payment_id, "estado": "pendiente"},
        {"$set": updates},
        return_document=ReturnDocument.AFTER)
    if doc is None:
        raise HTTPException(409, "Pago no encontrado o ya procesado")
    return strip_mongo(doc)


