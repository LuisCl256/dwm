"""Consumidor STOMP -> Mongo Analytics. ACK tras inserción idempotente; sin PII."""
from __future__ import annotations
import json
import logging
import os
import threading
import time
from datetime import timezone
from pydantic import ValidationError
import stomp
from pymongo.errors import DuplicateKeyError

from app.common import mongo_db, secret
from app.events import OrderCreated, PaymentApproved
from app.messaging.productor import DESTINATION

LOG = logging.getLogger("flor.events.consumer")


def ingest_event(raw: str) -> str:
    event = json.loads(raw)
    if not isinstance(event, dict):
        raise ValueError("Evento debe ser un objeto")
    event_type = event.get("event_type")
    if event_type == "order.created":
        obj = OrderCreated.model_validate(event)
    elif event_type == "payment.approved":
        obj = PaymentApproved.model_validate(event)
    else:
        raise ValueError("Tipo de evento no soportado")
    stored = obj.model_dump(mode="python")
    # UTC consistente para rangos; MongoDB almacena datetime UTC.
    stored["occurred_at"] = obj.occurred_at.astimezone(timezone.utc)
    try:
        mongo_db().events.insert_one(stored)
    except DuplicateKeyError:
        return "duplicado"
    return "almacenado"


class EventListener(stomp.ConnectionListener):
    def __init__(self, connection):
        self.connection = connection
        self.disconnected = threading.Event()

    def on_message(self, frame):
        # STOMP 1.2 usa el header ack; 1.1 puede usar message-id.
        ack_id = frame.headers.get("ack", frame.headers.get("message-id"))
        try:
            result = ingest_event(frame.body)
            LOG.info("Evento %s", result)
            self.connection.ack(id=ack_id)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError):
            LOG.error("Evento inválido; NACK sin reencolado (no contiene datos privados)")
            self.connection.nack(id=ack_id, headers={"requeue": "false"})
        except Exception as exc:
            LOG.warning("Fallo transitorio al persistir evento: %s", type(exc).__name__)
            self.connection.nack(id=ack_id, headers={"requeue": "true"})

    def on_disconnected(self):
        self.disconnected.set()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    mongo_db().events.create_index("event_id", unique=True)
    mongo_db().events.create_index([("event_type", 1), ("occurred_at", -1)])
    while True:
        conn = None
        try:
            conn = stomp.Connection12(
                [(os.getenv("BROKER_HOST", "broker"), 61613)],
                heartbeats=(10000, 10000),
                vhost="/"
            )

            listener = EventListener(conn)
            conn.set_listener("events", listener)
            conn.connect(login="flor_service", passcode=secret("rabbitmq-password"), wait=True, timeout=10)
            conn.subscribe(destination=DESTINATION, id="analytics", ack="client-individual",
                           headers={"prefetch-count": "10", "durable": "true"})
            LOG.info("Consumidor conectado a %s", DESTINATION)
            while not listener.disconnected.wait(timeout=10):
                pass
        except Exception as exc:
            LOG.warning("Reconectando consumidor: %s", type(exc).__name__)
        finally:
            if conn is not None and conn.is_connected():
                conn.disconnect()
            time.sleep(4)


if __name__ == "__main__":
    main()
