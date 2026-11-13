# Seguridad, secretos y tratamiento de datos sensibles

## Perímetro y redes

- Host → Gateway: `127.0.0.1:8000` (REST; solo localhost en esta etapa).
- Gateway → Inventory / Orders / Clients / Payments / Analytics / GraphQL: red interna Docker `private_api`, no puertos publicados.
- Servicios → MongoDB: red interna Docker `private_data`; MongoDB no está en `edge` ni tiene `ports`.
- No se confía solo en el Gateway: cada microservicio valida el JWT y aplica control de rol/propiedad.
- Solo `GET` del catálogo está disponible sin token. Rutas `/internal/*`, `/docs` y `/health` de cada microservicio no pueden pedirse mediante el proxy del Gateway.

## Token del usuario

- Inicio de sesión con nombre de cuenta y contraseña (`/auth/login`); contraseñas guardadas únicamente como hash Argon2id en Clients.
- JWT RS256: clave privada **solo en Gateway**; clave pública montada en cada servicio.
- Claims: `sub` (ID usuario), `role` (`client`, `employee`, `admin`), `iss`, `aud`, `iat`, `nbf`, `exp`.
- Expiración predeterminada: 30 minutos. No existe refresh token en esta primera etapa.
- Se aplica autorización **por recurso**: un JWT correcto de otro cliente no permite leer su pedido o pago.
- No se aceptan roles enviados por `/auth/register`, ni cabezales `X-Authenticated-Client` desde el navegador.

## Directorio de secretos

Ejecutar `python scripts/init_secrets.py` después de instalar `scripts/requirements.txt`. Genera automáticamente:

| Nombre en `secrets/` | Uso | Destinatarios |
|---|---|---|
| `jwt_private.pem` | Firmar JWT | Solo Gateway |
| `jwt_public.pem` | Validar JWT | Gateway y servicios |
| `service_token` | Auth para llamadas `/internal/*` | Gateway y servicios |
| `mongo-root-password` | Administrador técnico Mongo | Solo Mongo |
| `mongo-inventory-password` | Usuario DB Inventory | Mongo, Inventory |
| `mongo-orders-password` | Usuario DB Orders | Mongo, Orders |
| `mongo-clients-password` | Usuario DB Clients | Mongo, Clients |
| `mongo-payments-password` | Usuario DB Payments | Mongo, Payments y productor de pagos |
| `mongo-analytics-password` | Usuario DB Analytics | aprovisionador Mongo, Analytics y consumidor |
| `rabbitmq-password` | Contraseña RabbitMQ STOMP | Broker, productores y consumidor |

Cada archivo se monta **individualmente y como read-only**, solo en los contenedores que lo necesitan. El directorio `secrets/` figura en `.gitignore` y se excluye del ZIP entregado. Los secretos nunca se devuelven en respuestas HTTP. En sistemas POSIX el script intenta restringir el directorio del host a su propietario; en Windows depende de los permisos de tu cuenta local.

**Importante:** la primera etapa usa credenciales generadas en disco local para que `docker compose up` sea reproducible. El `gateway.py` anterior que leía HashiCorp Vault se conserva en `legacy/` pero **no está en uso** en este backend nuevo. Una etapa futura puede integrar Vault con políticas, roles y rotación de secretos, sin exponer un Vault dev token de root como falsa protección.

## Datos sensibles

- **Clients** almacena nombre, correo, teléfono y direcciones; solo permite leer datos propios o acceso del administrador.
- **Orders** conserva los datos de entrega y el detalle del pedido. Solo propietario o personal autorizado puede leerlos.
- **Payments** almacena identificador, monto CLP y estado **ficticio**; no almacena número de tarjeta, CVV ni claves bancarias.
- En consultas internas entre Payments y Orders solo viajan `client_id`, `numero_pedido`, `total` y `estado`, no domicilio ni correo.
- MongoDB usa bases y credenciales `readWrite` separadas para evitar el acceso indiscriminado entre dominios.
- Se recomienda política formal de retención/borrado, cifrado de volúmenes de host y auditoría antes de guardar datos reales de clientes.

## Limitaciones de seguridad que NO hay que confundir con producción

Se expone **HTTP local**, no HTTPS público. Para publicar el proyecto en Internet debe configurarse TLS con proxy inverso, CORS restrictivo, rate limiting, manejo de incidentes y logs adecuados; añadir revocación/sesiones, rotación de claves, protección ante fuerza bruta y copias de seguridad. La seguridad de la red Docker evita exposición directa pero **no equivale a cifrado TLS interno**. El secreto `service_token` es compartido dentro de la red interna; en una siguiente versión conviene usar identidades por servicio y permisos específicos. El modelo de inventario requiere conciliación de reservas y pagos antes de operar con dinero real.

## Comprobaciones rápidas

- `docker compose ps`: solo Gateway debe indicar puerto publicado (`127.0.0.1:8000`).
- `docker network inspect flor-vida_private_api`: ver componentes privados.
- `docker network inspect flor-vida_private_data`: ver DB y sus clientes.
- `python scripts/smoke_test.py`: valida HTTP 401 sin token, HTTP 403 ante una modificación no autorizada y HTTP 403 al intentar leer el pedido de otra cuenta.


## Etapa 2: superficie GraphQL y eventos

- `POST /graphql` es el único acceso externo a GraphQL; contenedor `graphql` sin puertos publicados y sin credenciales de Mongo. Valida tokens JWT y los servicios REST verifican propiedad/rol también. Tamaño de entrada limitado a 16 KiB; Strawberry limita profundidad (5), alias (10) y tokens (1500).
- `private_messaging` es una cuarta red `internal: true` reservada a RabbitMQ, productores y consumidor. El broker no publica TCP ni panel de administración al host. La configuración restringe a STOMP y deshabilita AMQP; los mensajes persistentes exigen secreto generado localmente.
- `Analytics` almacena únicamente identificadores de pedido y producto, tipo/fecha de evento, cantidad e importe; ningún dato de perfil, teléfono, email, domicilio ni identificador directo de cliente. El consumidor rechaza campos extra y aplica deduplicación por `event_id`.
- El aprovisionador `mongo_provision` usa la credencial root solo para crear el usuario Analytics, incluyendo migración desde una instalación persistente de la etapa 1. Termina tras ejecutar el script; no mantiene un servicio privilegiado disponible al usuario web.
- `payment.approved` genera únicamente **ingreso simulado**, no corresponde a una captura de tarjeta.
- Las conexiones entre contenedores son HTTP/STOMP en redes privadas. Esto NO equivale a TLS/mTLS, cifrado de datos en reposo ni protección frente a un host comprometido. No se recomienda almacenar datos reales de clientes antes de incorporar esos controles, rate limiting, auditoría, rotación y copias de seguridad.
