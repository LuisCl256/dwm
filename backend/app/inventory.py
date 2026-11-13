"""Inventory: catálogo y reserva atómica de existencias (Mongo)."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.catalog import PRODUCTS
from app.common import mongo_db, permit, require_internal, strip_mongo


def utcnow():
    return datetime.now(timezone.utc)


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=3, max_length=80)
    nombre: str = Field(min_length=2, max_length=120)
    categoria: str = Field(min_length=2, max_length=50)
    precio: int = Field(ge=0, le=100000000)
    descripcion: str = Field(min_length=5, max_length=1000)
    imagen: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    stock: int = Field(default=20, ge=0)


class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    categoria: str | None = Field(default=None, min_length=2, max_length=50)
    precio: int | None = Field(default=None, ge=0, le=100000000)
    descripcion: str | None = Field(default=None, min_length=5, max_length=1000)
    imagen: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    stock: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class ReservationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str
    quantity: int = Field(ge=1, le=50)


class Reservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservation_id: str = Field(min_length=5, max_length=80)
    items: list[ReservationItem] = Field(min_length=1, max_length=20)


@asynccontextmanager
async def lifespan(app: FastAPI):
    products = mongo_db().products
    products.create_index("id", unique=True)
    for product in PRODUCTS:
        products.update_one({"id": product["id"]}, {"$setOnInsert": {
            **product, "stock": 20, "activo": True, "creado_en": utcnow()
        }}, upsert=True)
    yield


app = FastAPI(title="Flor & Vida | Inventory (privado)", lifespan=lifespan)


@app.get("/health")
def health():
    mongo_db().command("ping")
    return {"status": "ok", "service": "inventory"}


@app.get("/products")
def products(category: str | None = None):
    # El listado público nunca expone productos desactivados.
    filt = {"activo": True}
    if category:
        filt["categoria"] = category
    return [strip_mongo(doc) for doc in mongo_db().products.find(filt)]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    doc = mongo_db().products.find_one({"id": product_id, "activo": True})
    if doc is None:
        raise HTTPException(404, "Producto no encontrado")
    return strip_mongo(doc)


@app.post("/products", status_code=201)
def create_product(data: ProductCreate, user: Annotated[dict, Depends(permit("admin"))]):
    doc = {**data.model_dump(), "activo": True, "creado_en": utcnow()}
    try:
        mongo_db().products.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, "ID de producto ya existe")
    return strip_mongo(doc)


@app.patch("/products/{product_id}")
def patch_product(product_id: str, data: ProductPatch, user: Annotated[dict, Depends(permit("admin"))]):
    updates = data.model_dump(exclude_unset=True)
    if not updates or any(v is None for k, v in updates.items() if k not in ("imagen", "color")):
        raise HTTPException(422, "Campos inválidos o vacíos")
    doc = mongo_db().products.find_one_and_update({"id": product_id}, {"$set": updates},
                                                   return_document=ReturnDocument.AFTER)
    if doc is None:
        raise HTTPException(404, "Producto no encontrado")
    return strip_mongo(doc)


@app.delete("/products/{product_id}")
def remove_product(product_id: str, user: Annotated[dict, Depends(permit("admin"))]):
    result = mongo_db().products.update_one({"id": product_id}, {"$set": {"activo": False}})
    if not result.matched_count:
        raise HTTPException(404, "Producto no encontrado")
    return {"eliminado": True, "modo": "desactivacion"}


@app.get("/internal/products/{product_id}", dependencies=[Depends(require_internal)])
def internal_product(product_id: str):
    doc = mongo_db().products.find_one({"id": product_id, "activo": True})
    if doc is None:
        raise HTTPException(404, "Producto no encontrado")
    return strip_mongo(doc)


@app.post("/internal/reserve", dependencies=[Depends(require_internal)])
def reserve(data: Reservation):
    reservations = mongo_db().reservations
    # ID único para impedir aplicar dos veces la misma reserva.
    try:
        reservations.insert_one({"_id": data.reservation_id, "state": "processing",
                                 "items": [i.model_dump() for i in data.items]})
    except DuplicateKeyError:
        raise HTTPException(409, "Reserva ya procesada o en proceso")
    reserved: list[ReservationItem] = []
    try:
        for item in data.items:
            result = mongo_db().products.update_one(
                {"id": item.product_id, "activo": True, "stock": {"$gte": item.quantity}},
                {"$inc": {"stock": -item.quantity}},
            )
            if not result.modified_count:
                raise HTTPException(409, f"Stock insuficiente: {item.product_id}")
            reserved.append(item)
        reservations.update_one({"_id": data.reservation_id}, {"$set": {"state": "reserved"}})
        return {"reserved": True, "reservation_id": data.reservation_id}
    except Exception:
        for item in reserved:
            mongo_db().products.update_one({"id": item.product_id}, {"$inc": {"stock": item.quantity}})
        reservations.update_one({"_id": data.reservation_id}, {"$set": {"state": "failed"}})
        raise


@app.post("/internal/release/{reservation_id}", dependencies=[Depends(require_internal)])
def release(reservation_id: str):
    res = mongo_db().reservations.find_one_and_update(
        {"_id": reservation_id, "state": "reserved"},
        {"$set": {"state": "releasing"}}, return_document=ReturnDocument.BEFORE)
    if res is None:
        raise HTTPException(409, "Reserva inexistente o ya liberada")
    for item in res["items"]:
        mongo_db().products.update_one({"id": item["product_id"]}, {"$inc": {"stock": item["quantity"]}})
    mongo_db().reservations.update_one({"_id": reservation_id}, {"$set": {"state": "released"}})
    return {"released": True}
