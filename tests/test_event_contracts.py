"""Pruebas unitarias de privacidad e integridad de eventos, sin Mongo/RabbitMQ."""
import unittest
from pydantic import ValidationError
from app.events import order_event, payment_event, OrderCreated


class ContractTests(unittest.TestCase):
    def test_evento_pedido_omite_pii(self):
        event = order_event("FV-2026-ABCDEFGHIJKL", 1000, [{
            "product_id": "ramo-aurora", "quantity": 1, "subtotal": 1000,
            "nombre": "Texto privado de producto"
        }])
        self.assertEqual(event["event_type"], "order.created")
        for pii in ["email", "telefono", "direccion", "client_id", "password_hash", "nombre"]:
            self.assertNotIn(pii, str(event))
        self.assertEqual(OrderCreated.model_validate(event).total, 1000)

    def test_prohibir_agregar_campo_pii(self):
        event = order_event("FV-2026-ABCDEFGHIJKL", 1000, [{
            "product_id": "ramo-aurora", "quantity": 1, "subtotal": 1000
        }])
        event["email"] = "persona@example.com"
        with self.assertRaises(ValidationError):
            OrderCreated.model_validate(event)

    def test_evento_pago(self):
        event = payment_event("FV-2026-ABCDEFGHIJKL", 18990)
        self.assertEqual(event["event_type"], "payment.approved")
        self.assertNotIn("client_id", event)
        self.assertEqual(event["total"], 18990)


if __name__ == "__main__":
    unittest.main()
