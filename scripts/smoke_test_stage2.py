"""Prueba etapa 2 desde el host. No requiere herramientas extra ni frontend.
Opcional: exportar ADMIN_EMAIL y ADMIN_PASSWORD para comprobar analítica y eventos pagos.
"""
import os
import sys
import time
from datetime import datetime, timedelta
from uuid import uuid4
from smoke_test import call


def graphql(query: str, token: str | None = None, variables: dict | None = None):
    response = call("POST", "/graphql", {"query": query, "variables": variables or {}}, token)
    if response.get("errors"):
        raise AssertionError(f"GraphQL: {response['errors']}")
    return response["data"]


def main():
    products = graphql("{ products { id nombre precio stock } }")["products"]
    assert any(p["id"] == "ramo-aurora" for p in products)
    print("1) GraphQL catálogo público: OK")
    identifier = uuid4().hex[:12]
    email = f"graphql-{identifier}@example.org"
    pwd = "Prueba-" + uuid4().hex + "!"
    data = {"nombre": "Usuario GraphQL Prueba", "email": email,
            "password": pwd, "telefono": "+56912345678"}
    call("POST", "/auth/register", data, expected=(201,))
    token = call("POST", "/auth/login", {"email": email, "password": pwd})["access_token"]
    date = (datetime.now() + timedelta(days=7)).date().isoformat()
    order = call("POST", "/api/orders/orders", {
        "nombre": data["nombre"], "email": email, "telefono": data["telefono"],
        "items": [{"product_id": "ramo-aurora", "quantity": 1}],
        "fecha": date, "direccion": "Calle de Ejemplo 123, Santiago"
    }, token, expected=(201,))
    payment = call("POST", "/api/payments/payments", {"numero_pedido": order["numero_pedido"]},
                   token, expected=(201,))
    query = '''query($number: String!) {
      orderOverview(orderNumber: $number) {
        order { numeroPedido estado total items { productId quantity subtotal } }
        payment { id estado monto moneda }
      }
    }'''
    overview = graphql(query, token, {"number": order["numero_pedido"]})["orderOverview"]
    assert overview["order"]["total"] == payment["monto"]
    assert overview["payment"]["id"] == payment["id"]
    print("2) GraphQL Orders + Payments, token propietario: OK")
    try:
        unauthorized = call("POST", "/graphql", {"query": query,
                               "variables": {"number": order["numero_pedido"]}})
        assert "errors" in unauthorized and unauthorized["data"]["orderOverview"] is None
    except KeyError:
        pass  # GraphQL podría omitir data cuando hay errores de autorización.
    print("3) GraphQL sin token protegido: OK")
    bad = call("POST", "/graphql", {"query": "{ products { id } }"},
               token=token + "alterado", expected=(401,))
    print("4) Gateway rechaza JWT adulterado: OK")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        admin_token = call("POST", "/auth/login",
                           {"email": admin_email, "password": admin_password})["access_token"]
        call("PATCH", f"/api/payments/payments/{payment['id']}", {"estado": "aprobado"},
             admin_token, expected=(200,))
        observed = False
        for _ in range(18):
            summary = call("GET", "/api/analytics/analytics/summary", token=admin_token)
            if summary["pedidos_creados"] >= 1 and summary["pagos_aprobados"] >= 1:
                observed = True
                break
            time.sleep(3)
        assert observed, "Los eventos aún no fueron procesados por el broker/consumidor"
        top = call("GET", "/api/analytics/analytics/products/top", token=admin_token)
        assert any(p["product_id"] == "ramo-aurora" for p in top)
        print("5) STOMP + Analytics + pago aprobado: OK")
    else:
        print("5) Sin ADMIN_EMAIL / ADMIN_PASSWORD: se omite validación de analítica y pago aprobado")
    print("OK - Verificaciones de etapa 2 completadas")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print("FALLO:", err, file=sys.stderr)
        sys.exit(1)
