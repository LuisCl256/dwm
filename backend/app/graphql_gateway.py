"""Gateway GraphQL interno: compone Inventory + Orders + Payments por sus REST.

Accesible solo a través de POST /graphql del Gateway REST; no hay datos Mongo directos.
Auth de propietario/rol sigue imponiéndose en microservicios, no solo en GraphQL.
"""
from __future__ import annotations
import os

import httpx
import strawberry
from fastapi import FastAPI, Request
from graphql import GraphQLError
from strawberry.extensions import MaxAliasesLimiter, MaxTokensLimiter, QueryDepthLimiter
from strawberry.fastapi import GraphQLRouter

from app.common import decode_token

BACKENDS = {
    "inventory": os.getenv("INVENTORY_URL", "http://inventory:8000"),
    "orders": os.getenv("ORDERS_URL", "http://orders:8000"),
    "payments": os.getenv("PAYMENTS_URL", "http://payments:8000"),
}


async def backend_get(name: str, path: str, authorization: str | None = None) -> dict | list | None:
    headers = {"Authorization": authorization} if authorization else {}
    try:
        async with httpx.AsyncClient(timeout=7.0) as client:
            response = await client.get(f"{BACKENDS[name]}{path}", headers=headers)
    except httpx.RequestError:
        raise GraphQLError("Servicio temporalmente no disponible")
    if response.status_code == 404:
        return None
    if response.status_code == 401:
        raise GraphQLError("Debes iniciar sesión")
    if response.status_code == 403:
        raise GraphQLError("Acceso denegado")
    if response.status_code != 200:
        raise GraphQLError("No se pudo completar la consulta")
    return response.json()


def authorized(info: strawberry.Info) -> str:
    header = info.context["request"].headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        raise GraphQLError("Debes iniciar sesión")
    # Esta validación rechaza tokens manipulados antes de realizar llamadas privadas.
    from fastapi import HTTPException
    try:
        decode_token(header.split(" ", 1)[1])
    except HTTPException:
        raise GraphQLError("Token inválido o vencido")
    return header


@strawberry.type
class Product:
    id: str
    nombre: str
    categoria: str
    precio: int
    descripcion: str
    stock: int


@strawberry.type
class OrderItem:
    product_id: str
    nombre: str
    quantity: int
    precio_unitario: int
    subtotal: int


@strawberry.type
class Order:
    numero_pedido: str
    estado: str
    fecha: str
    total: int
    items: list[OrderItem]


@strawberry.type
class Payment:
    id: str
    estado: str
    monto: int
    moneda: str


@strawberry.type
class OrderOverview:
    order: Order
    payment: Payment | None


@strawberry.type
class Query:
    @strawberry.field(description="Catálogo público actual sin acceso directo a Inventory")
    async def products(self, info: strawberry.Info) -> list[Product]:
        auth = info.context["request"].headers.get("authorization")
        rows = await backend_get("inventory", "/products", auth)
        return [Product(**{k: row[k] for k in Product.__dataclass_fields__}) for row in rows]

    @strawberry.field(description="Pedido y pago de ese pedido, validando el propietario en cada backend")
    async def order_overview(self, info: strawberry.Info, order_number: str) -> OrderOverview | None:
        auth = authorized(info)
        if len(order_number) > 80 or len(order_number) < 5:
            raise GraphQLError("Identificador de pedido inválido")
        order = await backend_get("orders", f"/orders/{order_number}", auth)
        if order is None:
            return None
        payment = await backend_get("payments", f"/payments/by-order/{order_number}", auth)
        order_data = Order(numero_pedido=order["numero_pedido"], estado=order["estado"],
                           fecha=order["fecha"], total=order["total"],
                           items=[OrderItem(**line) for line in order["items"]])
        payment_data = (Payment(**{k: payment[k] for k in Payment.__dataclass_fields__})
                        if payment is not None else None)
        return OrderOverview(order=order_data, payment=payment_data)


schema = strawberry.Schema(query=Query, extensions=[
    lambda: QueryDepthLimiter(max_depth=5),
    lambda: MaxAliasesLimiter(max_alias_count=10),
    lambda: MaxTokensLimiter(max_token_count=1500),
])
app = FastAPI(title="Flor & Vida | GraphQL Gateway (privado)")
app.include_router(GraphQLRouter(schema, graphql_ide=None, allow_queries_via_get=False), prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "ok", "service": "graphql"}
