"""Analítica administrativa de eventos anonimizados (solo agregados)."""
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Query
from app.common import mongo_db, permit


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_db().events.create_index("event_id", unique=True)
    mongo_db().events.create_index([("event_type", 1), ("occurred_at", -1)])
    yield


app = FastAPI(title="Flor & Vida | Analytics (privado)", lifespan=lifespan)


@app.get("/health")
def health():
    mongo_db().command("ping")
    return {"status": "ok", "service": "analytics"}


def date_filter(since: date | None, until: date | None) -> dict:
    if since and until and since > until:
        from fastapi import HTTPException
        raise HTTPException(422, "Desde no puede ser posterior a hasta")
    filt = {}
    if since:
        filt["$gte"] = datetime.combine(since, time.min, tzinfo=timezone.utc)
    if until:
        filt["$lt"] = datetime.combine(until + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return {"occurred_at": filt} if filt else {}


@app.get("/analytics/summary")
def summary(user: Annotated[dict, Depends(permit("admin"))],
            desde: date | None = None, hasta: date | None = None):
    date_range = date_filter(desde, hasta)
    pipeline = [
        {"$match": date_range},
        {"$group": {"_id": "$event_type", "cantidad": {"$sum": 1},
                    "monto_clp": {"$sum": "$total"}}},
    ]
    rows = {d["_id"]: d for d in mongo_db().events.aggregate(pipeline)}
    orders = rows.get("order.created", {})
    paid = rows.get("payment.approved", {})
    return {"pedidos_creados": orders.get("cantidad", 0),
            "importe_pedidos_clp": orders.get("monto_clp", 0),
            "pagos_aprobados": paid.get("cantidad", 0),
            "ingresos_simulados_clp": paid.get("monto_clp", 0),
            "filtro": {"desde": desde, "hasta": hasta},
            "nota": "Analítica asincrónica; los indicadores pueden tardar segundos en actualizarse"}


@app.get("/analytics/products/top")
def top_products(user: Annotated[dict, Depends(permit("admin"))],
                 limit: int = Query(5, ge=1, le=20),
                 desde: date | None = None, hasta: date | None = None):
    filter_events = {**date_filter(desde, hasta), "event_type": "order.created"}
    pipeline = [
        {"$match": filter_events},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.product_id", "unidades": {"$sum": "$items.quantity"},
                    "importe_pedido_clp": {"$sum": "$items.subtotal"}}},
        {"$sort": {"unidades": -1, "_id": 1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "product_id": "$_id", "unidades": 1, "importe_pedido_clp": 1}},
    ]
    return list(mongo_db().events.aggregate(pipeline))
