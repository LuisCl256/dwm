# Rutas REST y permisos por stakeholder

Base: `http://127.0.0.1:8000` (único puerto publicado). JWT: `Authorization: Bearer <token>`. En la matriz, `—` significa denegado. El Gateway solo permite las familias públicas listadas, nunca `/internal/*`.

| Recurso / ruta pública | Método | Visitante | Client | Employee | Admin |
|---|---|---:|---:|---:|---:|
| `/health` | GET | ✓ | ✓ | ✓ | ✓ |
| `/auth/register` | POST | ✓ | ✓ | ✓ | ✓ |
| `/auth/login` | POST | ✓ | ✓ | ✓ | ✓ |
| `/api/inventory/products` | GET | ✓ | ✓ | ✓ | ✓ |
| `/api/inventory/products/{id}` | GET | ✓ | ✓ | ✓ | ✓ |
| `/api/inventory/products` | POST | — | — | — | ✓ |
| `/api/inventory/products/{id}` | PATCH | — | — | — | ✓ |
| `/api/inventory/products/{id}` | DELETE | — | — | — | ✓ |
| `/api/clients/clients/me` | GET, PATCH | — | sí, propios | sí, propios | sí, propios |
| `/api/clients/clients` | GET | — | — | — | ✓ |
| `/api/clients/clients/{id}` | GET | — | solo propia | solo propia | ✓ |
| `/api/clients/clients/{id}` | DELETE | — | — | — | ✓ |
| `/api/orders/orders` | POST | — | ✓ | ✓ | ✓ |
| `/api/orders/orders` | GET | — | solo propios | ✓ | ✓ |
| `/api/orders/orders/{numero}` | GET | — | solo propio | ✓ | ✓ |
| `/api/orders/orders/{numero}` | PATCH | — | cancelar propio | ✓ | ✓ |
| `/api/payments/payments` | POST | — | pedido propio | ✓ | ✓ |
| `/api/payments/payments` | GET | — | solo propios | solo propios | ✓ |
| `/api/payments/payments/{id}` | GET | — | solo propio | solo propio | ✓ |
| `/api/payments/payments/{id}` | PATCH | — | — | — | ✓ |
| `/api/payments/payments/by-order/{numero}` | GET | — | propio | propio | ✓ |
| `/api/analytics/analytics/summary` | GET | — | — | — | ✓ |
| `/api/analytics/analytics/products/top` | GET | — | — | — | ✓ |
| `/graphql` (`products`) | POST | ✓ | ✓ | ✓ | ✓ |
| `/graphql` (`orderOverview`) | POST | — | propio | según permisos Orders+Payments | ✓ |

**Importante:** `employee` y `admin` no se registran mediante `/auth/register`; se crean exclusivamente desde CLI privado en el contenedor `clients`. El CLI privado permite elegir `admin` o `employee`, sin exponer la elevación de privilegios como endpoint público.

### Ejemplos de solicitudes

**Registrar:** POST `/auth/register`

```json
{"nombre":"María Ejemplo","email":"maria@example.com","password":"ClaveSegura12345!","telefono":"+56912345678"}
```

**Iniciar sesión:** POST `/auth/login`

```json
{"email":"maria@example.com","password":"ClaveSegura12345!"}
```

**Crear pedido:** POST `/api/orders/orders` (Bearer)

```json
{
  "nombre":"María Ejemplo",
  "email":"maria@example.com",
  "telefono":"+56912345678",
  "items":[{"product_id":"ramo-aurora","quantity":1}],
  "fecha":"2027-01-15",
  "direccion":"Calle Ejemplo 123, Santiago",
  "mensaje":"Feliz cumpleaños"
}
```

La fecha debe ser igual o posterior a la fecha local de Chile en el momento de la operación. El servidor consulta el precio, calcula `total` y reserva el stock; **no acepta precios proporcionados por el cliente**.

**Crear un pago SIMULADO:** POST `/api/payments/payments` (Bearer)

```json
{"numero_pedido":"FV-2026-XXXXXXXXXXXX"}
```

El servidor consulta Orders para obtener el importe exacto. El estado de un pago ficticio se puede cambiar a `aprobado` o `rechazado` mediante PATCH por un administrador. No se realiza ningún cobro real.

### Eliminación y trazabilidad

- `DELETE` Inventory **desactiva** el producto para mantener el historial de pedidos.
- `DELETE` Clients **desactiva** la cuenta. Una implementación de derecho de supresión requiere un proceso adicional de anonimización/retención documentada.
- Orders no se elimina físicamente; el cliente puede cancelar su propio pedido antes del despacho, y un empleado puede actualizar su estado.
- Payments no se elimina físicamente por trazabilidad; se registra como `rechazado` cuando corresponda.

### Rutas internas nunca públicas

| Ruta privada | Quién la invoca | Propósito |
|---|---|---|
| `clients:8000/internal/register` | Gateway | crear cuenta de cliente |
| `clients:8000/internal/login` | Gateway | verificar credenciales |
| `inventory:8000/internal/products/{id}` | Orders | validar referencia y precio |
| `inventory:8000/internal/reserve` | Orders | reservar stock |
| `inventory:8000/internal/release/{id}` | Orders | liberar stock cancelado |
| `orders:8000/internal/orders/{numero}` | Payments | propietario, estado e importe |

Las rutas internas requieren el encabezado `X-Internal-Secret`, solo usado entre servicios. No hay rutas públicas para revelar secretos ni credenciales de MongoDB.


## Etapa 2: contratos adicionales

`POST /graphql` recibe JSON con campos `query` y `variables`. GraphQL expone `products` y `orderOverview(orderNumber: String!)`, cada propiedad tiene control RBAC/propietario en el backend. Los errores GraphQL pueden responder HTTP 200 y `errors`. El esquema privado no se publica con IDE. La API del Gateway sigue siendo el único punto HTTP del host.

`GET /api/analytics/analytics/summary` y `/api/analytics/analytics/products/top` son **solo administradores**; permiten `desde` y `hasta` opcionales como fechas UTC (y `limit` para ranking). La semántica e integración del broker están documentadas en [graphql_eventos_analitica.md](graphql_eventos_analitica.md).
