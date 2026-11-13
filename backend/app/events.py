"""Contratos de eventos mínimos: sin datos personales, idempotentes para analítica."""
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class SaleLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(min_length=3, max_length=80)
    quantity: int = Field(ge=1, le=50)
    subtotal: int = Field(ge=0)


class OrderCreated(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=32, max_length=36)
    event_type: Literal["order.created"]
    occurred_at: datetime
    numero_pedido: str = Field(min_length=8, max_length=80)
    total: int = Field(ge=0)
    items: list[SaleLine] = Field(min_length=1, max_length=20)

class PaymentApproved(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=32, max_length=36)
    event_type: Literal["payment.approved"]
    occurred_at: datetime
    numero_pedido: str = Field(min_length=8, max_length=80)
    total: int = Field(ge=0)


def order_event(number: str, total: int, items: list[dict]) -> dict:
    return OrderCreated(
        event_id=str(uuid4()), event_type="order.created", occurred_at=datetime.now(timezone.utc),
        numero_pedido=number, total=total,
        items=[SaleLine(product_id=i["product_id"], quantity=i["quantity"], subtotal=i["subtotal"])
               for i in items],
    ).model_dump(mode="json")


def payment_event(number: str, total: int) -> dict:
    return PaymentApproved(event_id=str(uuid4()), event_type="payment.approved",
                           occurred_at=datetime.now(timezone.utc), numero_pedido=number,
                           total=total).model_dump(mode="json")
