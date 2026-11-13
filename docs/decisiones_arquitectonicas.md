# Decisiones arquitectónicas y justificación

## 1. ¿Por qué Docker Compose?

Se eligió **Docker Compose** porque la consigna permite demostrar la separación pública/privada en un entorno reproducible sin requerir nube pagada.

Beneficios:

- Reproducibilidad local para evaluación.
- Aislamiento de servicios y redes.
- Posibilidad de dejar el frontend fuera por ahora y conectarlo después.
- Facilita mostrar que el usuario solo ve el Gateway, mientras MongoDB, RabbitMQ y los servicios quedan privados.

## 2. ¿Por qué microservicios “ligeros” y no un monolito?

El proyecto exige distinguir sistemas como **Inventory, Orders, Clients y Payments**. Separarlos en servicios ayuda a:

- asignar responsabilidades claras,
- justificar permisos distintos,
- aislar datos sensibles,
- y mostrar una arquitectura moderna y extensible.

Sin embargo, se mantuvo una implementación contenida y académica: todos los servicios usan el mismo stack (FastAPI + MongoDB) para reducir complejidad innecesaria.

## 3. ¿Por qué un Gateway REST y otro GraphQL?

### Gateway REST

Es la entrada pública única. Su función es:

- autenticar,
- verificar JWT,
- recibir las solicitudes del cliente,
- y redirigir a los servicios apropiados.

### Gateway GraphQL

Se añadió para cumplir el requerimiento de **agregación** entre servicios. Su objetivo no es reemplazar REST, sino permitir consultas compuestas como:

- pedido + pago,
- catálogo resumido,
- futura composición para frontend.

GraphQL no accede a bases de datos directamente; solo consume los servicios privados ya existentes.

## 4. ¿Por qué no integrar el frontend todavía?

La consigna actual pide terminar el backend de forma segura y completa, **sin necesidad de integrarlo aún con el frontend**. Por eso:

- el frontend original se preserva tal como estaba,
- se utilizan sus datos como referencia,
- y el backend queda preparado para conectarse después.

Esto reduce riesgo y acelera la entrega.

## 5. ¿Por qué pagos simulados?

El proyecto es académico y no necesita operar con dinero real. Implementar pagos simulados evita:

- almacenar datos bancarios,
- introducir riesgos de seguridad innecesarios,
- y depender de proveedores externos.

Por eso el servicio Payments solo registra operaciones ficticias con estados como `pendiente`, `aprobado` o `rechazado`.

## 6. ¿Por qué proteger los secretos fuera del código?

Las credenciales de MongoDB, RabbitMQ y las llaves JWT no deben quedar escritas en el código fuente porque:

- se exponen si el repositorio se comparte,
- dificultan su rotación,
- y mezclan configuración sensible con lógica de aplicación.

Se eligió generar secretos localmente mediante `scripts/init_secrets.py` y montarlos como archivos de solo lectura en los contenedores.

## 7. ¿Por qué separar datos por servicio?

Cada dominio tiene su propia base Mongo y usuario `readWrite`:

- `flor_inventory`
- `flor_orders`
- `flor_clients`
- `flor_payments`
- `flor_analytics`

Esto minimiza el acceso lateral y ayuda a justificar la **naturaleza privada** de cada servicio.

## 8. ¿Por qué usar mensajería STOMP y analítica?

La mensajería permite desacoplar eventos importantes del flujo principal:

- creación de pedidos,
- aprobación de pagos,
- generación de métricas.

STOMP se mantuvo por continuidad con los archivos originales `productor.py` y `consumidor.py`, que la consigna ya contemplaba como plantillas adaptables.

La analítica se alimenta de eventos y no de lectura directa de datos operacionales. Esto reduce el acoplamiento y evita exponer información personal.

## 9. ¿Por qué no usar gRPC?

Aunque la consigna lo menciona, también condiciona su uso a que **las necesidades del caso lo justifiquen**.

En esta entrega se decidió **no incorporarlo** por las siguientes razones:

1. Las llamadas internas son simples y de bajo volumen.
2. No hay necesidad de streaming ni comunicación de muy baja latencia.
3. REST ya cubre correctamente las operaciones entre servicios.
4. Añadir gRPC solo para “cumplir” aumentaría complejidad sin beneficio real para este caso.

En otras palabras, el proyecto sí analiza gRPC, pero concluye razonadamente que **no es necesario en esta fase**.

## 10. ¿Qué quedaría para una siguiente fase?

- Integración completa con el frontend.
- CORS y políticas de despliegue web.
- Refresh tokens o revocación de JWT.
- TLS/HTTPS real.
- Saga más robusta entre Orders e Inventory.
- Rate limiting y observabilidad.
- Eventual incorporación de gRPC si el sistema creciera o aparecieran necesidades de rendimiento específicas.
