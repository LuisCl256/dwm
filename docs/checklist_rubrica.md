# Checklist de cumplimiento de la rúbrica

Esta tabla resume **qué pide la consigna** y **dónde se evidencia** dentro del proyecto.

| Requisito | Estado | Evidencia principal |
|---|---|---|
| Identificar y desarrollar servicios para agregar, modificar, eliminar y consultar información | Cumplido | `backend/app/{inventory,orders,clients,payments}.py`, `README.md` |
| Modelar clases y cardinalidades | Cumplido | `docs/arquitectura.md` |
| Definir al menos los sistemas Inventory, Orders, Clients y Payments | Cumplido | `backend/app/*.py`, `compose.yaml` |
| Asignar permisos HTTP a los stakeholders | Cumplido | `docs/rutas_y_permisos.md`, `README.md` |
| Diseñar el o los API Gateway | Cumplido | `backend/app/gateway.py`, `backend/app/graphql_gateway.py`, `docs/arquitectura.md` |
| Documentar rutas y secretos de integración | Cumplido | `README.md`, `docs/rutas_y_permisos.md`, `docs/seguridad_y_secretos.md` |
| Justificar protección de datos sensibles y secretos asociados al cliente | Cumplido | `docs/seguridad_y_secretos.md`, `docs/decisiones_arquitectonicas.md` |
| Separar servicios privados por su naturaleza | Cumplido | `compose.yaml`, `docs/arquitectura.md` |
| Implementar agregaciones mediante GraphQL Gateway | Cumplido | `backend/app/graphql_gateway.py`, `docs/graphql_eventos_analitica.md` |
| Utilizar gRPC y analítica cuando las necesidades del caso lo justifiquen | Parcial justificado | Analítica sí implementada (`backend/app/analytics.py`); gRPC **no implementado** y **justificado** en `README.md` y `docs/decisiones_arquitectonicas.md` |
| Incluir un README completo y bien estructurado | Cumplido | `README.md` |
| Demostrar separación pública y privada mediante contenedores u otro entorno reproducible | Cumplido | `compose.yaml`, redes Docker `edge`, `private_api`, `private_data`, `private_messaging` |

## Observación importante sobre gRPC

La consigna indica utilizar gRPC **cuando las necesidades del caso lo justifiquen**. En esta entrega se dejó documentada la decisión de **no incorporarlo** en esta iteración, porque:

1. El proyecto es pequeño y local.
2. Las interacciones internas actuales son simples y síncronas.
3. REST ya cubre las operaciones privadas sin introducir complejidad adicional.
4. No hay requisitos de streaming, latencia crítica ni contratos binarios de alto rendimiento.

Por lo tanto, la interpretación adoptada es: **se justifica su no uso** en esta fase, en vez de integrarlo artificialmente.

## Qué componentes son “activos” y cuáles quedan como referencia

- **Activos**: `backend/app/`, `compose.yaml`, `docs/`, `scripts/`, `tests/`.
- **Referenciales**: `legacy/` contiene los archivos originales preservados, sin uso en la versión final.

## Nivel de verificación alcanzado

- Sintaxis Python revisada.
- Estructura de Compose revisada.
- Pruebas unitarias de eventos incluidas.
- Smoke tests incluidos.
- **No se certifica aquí una ejecución integral con Docker**, porque el entorno de preparación no disponía de Docker.

Esto debe presentarse como **implementación completa y preparada para ejecución local**, no como validación empírica final ya realizada.
