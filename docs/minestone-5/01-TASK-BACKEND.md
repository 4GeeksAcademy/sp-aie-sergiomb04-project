# Objetivo

Completa íntegramente el Hito 5 de backend implementando un sistema de gestión de inventario sobre el servicio FastAPI existente, respetando todas las reglas de negocio, arquitectura y criterios de aceptación.

## Requisitos obligatorios

- Lee [00-CONTEXT-company.md](00-CONTEXT-company.md) antes de crear modelos, schemas o endpoints y adapta entidades, campos y restricciones exactamente a ese contexto.
- Mantén TinyDB exclusivamente para autenticación y usuarios.
- Implementa una segunda conexión a Supabase/PostgreSQL mediante SQLModel para todo el dominio de inventario.
- Nunca mezcles datos de negocio en TinyDB ni usuarios en Supabase.

## Base de datos

- Añade `DATABASE_URL` a `.env`.
- Inicializa ambas conexiones en `database.py` (o equivalente).
- Implementa `get_db()` usando `Depends()` para crear una sesión SQLModel por petición.
- No utilices sesiones globales.
- Ejecuta `SQLModel.metadata.create_all(engine)` al iniciar la aplicación.

## Modelos ORM

Crea en `models.py`:

- `Product`
- `InboundOrder`
- `OutboundOrder`

Requisitos:

- SQLModel con `table=True`.
- `InboundOrder.product_id` y `OutboundOrder.product_id` deben ser Foreign Keys hacia `Product`.
- `user_uuid` es un string que referencia usuarios de TinyDB, sin FK.
- Incluye todos los campos obligatorios definidos por el CONTEXT.

## Schemas

En `schemas.py` crea modelos Pydantic independientes de los ORM para:

- Product
- InboundOrder
- OutboundOrder

El schema de respuesta de Product debe incluir:

- `current_stock` (calculado, nunca almacenado)

No devuelvas modelos ORM desde ningún endpoint.

## Router

Crea `routers/inventory.py` con:

- `APIRouter(prefix="/inventory")`

Regístralo en la aplicación principal.

Implementa:

- `GET /inventory/products`
- `POST /inventory/products` (autenticado)
- `GET /inventory/products/{id}`
- `POST /inventory/orders/inbound` (autenticado)
- `POST /inventory/orders/outbound` (autenticado)
- `GET /inventory/orders`

## Reglas de negocio

- El stock nunca puede almacenarse ni modificarse directamente.
- `current_stock` debe calcularse siempre como:

  entradas - salidas

- Todo producto comienza con stock 0.
- Solo las órdenes modifican el inventario.
- Las órdenes deben guardar el `user_uuid` del usuario autenticado.
- Antes de crear una orden de salida valida que existe stock suficiente.
- Si el stock sería negativo devuelve HTTP 400 y no persistas la orden.

## Implementación

- Evita el problema N+1 cargando correctamente las relaciones.
- Mantén separados ORM y Schemas.
- Utiliza SQLModel, no SQLAlchemy directamente.
- Usa variables de entorno para todas las credenciales.
- Asegúrate de que `.env` esté incluido en `.gitignore`.

## Verificación final

Comprueba que:

- Existen dos conexiones de base de datos funcionando.
- TinyDB solo se usa para autenticación.
- Supabase contiene todos los datos de inventario.
- Todos los endpoints funcionan bajo `/inventory`.
- Las Foreign Keys están correctamente definidas.
- Ningún endpoint permite modificar el stock directamente.
- El stock se calcula a partir del historial de órdenes.
- Las órdenes almacenan `user_uuid`.
- Los modelos ORM y los schemas están separados.
- Todas las sesiones SQLModel se crean mediante `Depends()`.
- Los nombres de entidades y campos coinciden exactamente con [00-CONTEXT-company.md](00-CONTEXT-company.md).
