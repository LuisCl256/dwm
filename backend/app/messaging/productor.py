"""Publicador STOMP del outbox embebido: una instancia por colección y servicio Mongo.

El evento se guarda en la misma inserción/actualización Mongo que el recurso.
Se marca enviado SOLO tras recibir RECEIPT del broker (confirmación de persistencia).
Una caída posterior al receipt puede duplicar el envío; el consumidor es idempotente.
"""
from __future__ import annotations
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

import stomp
from pymongo import ReturnDocument
from app.common import mongo_db, secret

LOG = logging.getLogger("flor.events.producer")
DESTINATION = "/queue/flor_orders_events"


class ReceiptListener(stomp.ConnectionListener):
    def __init__(self):
        self.receipts: set[str] = set()
        self.error: str | None = None
        self.condition = threading.Condition()

    def on_receipt(self, frame):
        with self.condition:
            self.receipts.add(frame.headers.get("receipt-id", ""))
            self.condition.notify_all()

    def on_error(self, frame):
        with self.condition:
            self.error = "Error informado por broker STOMP"
            self.condition.notify_all()

    def on_disconnected(self):
        with self.condition:
            self.error = "Broker desconectado"
            self.condition.notify_all()

    def confirm(self, receipt_id: str, timeout: float = 12) -> bool:
        with self.condition:
            self.condition.wait_for(lambda: receipt_id in self.receipts or self.error, timeout=timeout)
            return receipt_id in self.receipts


def connect():
    conn = stomp.Connection12(
        [(os.getenv("BROKER_HOST", "broker"), 61613)],
        heartbeats=(10000, 10000),
        vhost="/"
    )
    listener = ReceiptListener()
    conn.set_listener("receipts", listener)
    conn.connect(login="flor_service", passcode=secret("rabbitmq-password"), wait=True, timeout=10)
    return conn, listener


def publish_pending():
    collection_name = os.environ["EVENT_COLLECTION"]
    if collection_name not in {"orders", "payments"}:
        raise RuntimeError("EVENT_COLLECTION no permitida")
    collection = mongo_db()[collection_name]
    connection, listener = connect()
    count = 0
    try:
        for record in collection.find({"_outbox.sent_at": {"$exists": False},
                                       "_outbox.event": {"$exists": True}}).limit(40):
            event = record["_outbox"]["event"]
            receipt_id = str(uuid4())
            connection.send(destination=DESTINATION, body=json.dumps(event, separators=(",", ":")),
                            headers={"persistent": "true", "receipt": receipt_id,
                                     "content-type": "application/json"})
            if not listener.confirm(receipt_id):
                raise RuntimeError("El broker no confirmó la persistencia del mensaje")
            # CAS: solo se marca enviado el evento confirmado; otro evento no puede marcarse por error.
            updated = collection.find_one_and_update(
                {"_id": record["_id"], "_outbox.event.event_id": event["event_id"],
                 "_outbox.sent_at": {"$exists": False}},
                {"$set": {"_outbox.sent_at": datetime.now(timezone.utc)}},
                return_document=ReturnDocument.AFTER)
            if updated is not None:
                count += 1
    finally:
        connection.disconnect()
    return count


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    LOG.info("Productor STOMP iniciado: colección %s", os.environ.get("EVENT_COLLECTION"))
    while True:
        try:
            count = publish_pending()
            if count:
                LOG.info("Eventos confirmados: %s", count)
            time.sleep(3)
        except Exception as exc:
            LOG.warning("Publicación diferida: %s", type(exc).__name__)
            time.sleep(5)


if __name__ == "__main__":
    main()
