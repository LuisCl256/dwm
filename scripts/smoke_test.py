"""Prueba funcional del Gateway desplegado. Crea cuentas y un pedido de demostración."""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from uuid import uuid4

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")


def call(method, route, data=None, token=None, expected=(200,)):
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(BASE + route, data=json.dumps(data).encode() if data is not None else None,
                  headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as response:
            status = response.status
            text = response.read().decode()
    except HTTPError as exc:
        status = exc.code
        text = exc.read().decode()
    if status not in expected:
        raise AssertionError(f"{method} {route}: HTTP {status}, se esperaba {expected}: {text}")
    return json.loads(text) if text else {}


def main():
    print("1) Gateway disponible")
    assert call("GET", "/health")["status"] == "ok"
    print("2) Inventario público y catálogo original")
    prods = call("GET", "/api/inventory/products")
    assert len(prods) >= 9
    original = next(p for p in prods if p["id"] == "ramo-aurora")
    assert original["precio"] == 18990
    print("3) Acceso a órdenes sin token prohibido")
    call("GET", "/api/orders/orders", expected=(401,))
    print("4) Crear usuario, autenticar y consultar perfil")
    email = f"prueba-{uuid4().hex[:10]}@example.org"
    password = "ClaveDePrueba-" + uuid4().hex[:12]
    reg = {"nombre": "Cliente de Prueba", "email": email, "password": password, "telefono": "+56912345678"}
    call("POST", "/auth/register", reg, expected=(201,))
    token = call("POST", "/auth/login", {"email": email, "password": password})["access_token"]
    profile = call("GET", "/api/clients/clients/me", token=token)
    assert profile["email"] == email and "password_hash" not in profile
    print("5) Prohibir modificación de producto al cliente")
    call("PATCH", "/api/inventory/products/ramo-aurora", {"precio": 1}, token, expected=(403,))
    print("6) Crear pedido (precio calculado en servidor, reserva de stock)")
    delivery = (datetime.now() + timedelta(days=3)).date().isoformat()
    order = call("POST", "/api/orders/orders", {
        "nombre": "Cliente de Prueba", "email": email, "telefono": "+56912345678",
        "items": [{"product_id": "ramo-aurora", "quantity": 1}],
        "fecha": delivery, "direccion": "Avenida de las Flores 123, Santiago",
        "mensaje": "Entregar en recepción"
    }, token, expected=(201,))
    assert order["total"] == 18990 and order["items"][0]["product_id"] == "ramo-aurora"
    print("7) Registrar pago ficticio; monto no editable por cliente")
    payment = call("POST", "/api/payments/payments", {"numero_pedido": order["numero_pedido"]}, token, expected=(201,))
    assert payment["monto"] == order["total"] and payment["metodo"] == "simulacion"
    print("8) Intento de consulta ajena: denegado")
    other_email = f"otro-{uuid4().hex[:10]}@example.org"
    call("POST", "/auth/register", {**reg, "email": other_email}, expected=(201,))
    other_token = call("POST", "/auth/login", {"email": other_email, "password": password})["access_token"]
    call("GET", f"/api/orders/orders/{order['numero_pedido']}", token=other_token, expected=(403,))
    print("OK - Smoke test completo. Pedido de prueba:", order["numero_pedido"])
    print("NOTA: El test inserta dos clientes, un pedido y un pago SIMULADO.")


if __name__ == "__main__":
    try:
        main()
    except (URLError, AssertionError, ValueError) as exc:
        print(f"PRUEBA FALLIDA: {exc}", file=sys.stderr)
        sys.exit(1)
