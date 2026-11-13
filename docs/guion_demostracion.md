# Guion breve de demostración / defensa

Este documento sirve como apoyo si necesitas **explicar rápidamente** el proyecto frente al profesor.

## 1. Introducción

> “Flor & Vida es una tienda virtual de florería. El frontend ya existía y en esta etapa se implementó un backend completo, seguro y modular, con separación de servicios, control de permisos, API Gateway, GraphQL, mensajería y analítica, todo ejecutable localmente con Docker Compose.”

## 2. Arquitectura

Puntos clave a mencionar:

1. **Gateway REST**: única entrada pública.
2. **Servicios privados**: Inventory, Orders, Clients, Payments y Analytics.
3. **MongoDB**: bases separadas por dominio.
4. **RabbitMQ + STOMP**: eventos de pedidos y pagos.
5. **GraphQL**: agrega datos de varios servicios.
6. **Docker Compose**: demuestra separación pública/privada sin nube.

## 3. Stakeholders

- **Visitante**: ve el catálogo.
- **Cliente**: registra cuenta, hace pedidos y consulta lo suyo.
- **Empleado**: gestiona pedidos autorizados.
- **Administrador**: gestiona productos, pagos simulados y analítica.

## 4. Seguridad

Puntos clave:

- JWT con firma RS256.
- Contraseñas con Argon2id.
- Secretos fuera del código.
- Mongo y RabbitMQ sin puertos públicos.
- Control de acceso por rol y por propiedad del recurso.
- Eventos de analítica sin datos personales.

## 5. GraphQL y mensajería

- GraphQL permite pedir en una sola consulta información agregada.
- Orders y Payments emiten eventos.
- Analytics consume esos eventos y genera métricas.
- Esto desacopla el flujo principal de la generación de reportes.

## 6. Justificación de gRPC

> “Se evaluó usar gRPC, pero no se implementó porque el caso no lo necesita aún: el volumen es bajo, no hay streaming y REST es suficiente para la comunicación interna.”

## 7. Cierre

> “La solución queda lista para ejecución local, demostración y futura integración con el frontend. Se priorizó seguridad, separación de responsabilidades y reproducibilidad.”
