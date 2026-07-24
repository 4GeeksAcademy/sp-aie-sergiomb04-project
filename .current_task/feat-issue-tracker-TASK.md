## Objetivo

Implementar un **Gestor de Incidencias Centralizado** sobre el monorepo existente. Leer primero `CONTEXT-company.md` y usar exactamente sus categorías, sedes y valores.

### Backend

* Crear el modelo `Incident` con los campos:

  * `id`
  * `title`
  * `description`
  * `category`
  * `status`
  * `origin`
  * `branch`
  * `created_at`
  * `updated_at`
* Validar campos obligatorios y enums:

  * `status`: `open`, `in_progress`, `resolved`, `discarded`
  * `origin`: `customer`, `branch`, `internal`
  * `category`: según `CONTEXT-company.md`
* Crear `scripts/seed_incidents.py`:

  * Importar el CSV del proyecto anterior.
  * Asignar `origin="customer"` a todos los registros.
  * Reutilizar validaciones desde `packages/shared`.
  * Ignorar y reportar registros inválidos.
  * Ser idempotente (no duplicar datos).
* Implementar endpoints:

  * `POST /api/incidents`
  * `GET /api/incidents` (filtros: `status`, `origin`, `branch`, `category`)
  * `GET /api/incidents/{id}`
  * `PATCH /api/incidents/{id}/status`
  * `GET /api/incidents/summary`
* Validar transiciones de estado:

  * `open → in_progress | discarded`
  * `in_progress → resolved | discarded`
  * `resolved` y `discarded` son estados finales.
* Manejo de errores:

  * `400` con `{ field, message }` para validaciones.
  * `404` si no existe.
  * `500` genérico, nunca devolver stack trace.
  * Si no hay datos, devolver listas vacías o métricas en `0`.

### Frontend

* Crear página de registro de incidencias.
* Formulario con todos los campos; `branch` obligatorio y siempre visible.
* Resaltar `branch` cuando `origin="branch"`.
* Mostrar loading y deshabilitar el botón al enviar.
* Mostrar errores amigables y por campo.
* Limpiar el formulario y mostrar confirmación tras guardar.
* Crear listado con filtros (`status`, `origin`, `branch`), loading, estado vacío, reintento si falla y actualización de estado con rollback visual si falla.
* Crear panel de resumen consumiendo `/summary`, con loading y manejo de errores sin romper la UI.

### Requisitos

* Reutilizar toda la lógica de validación en `packages/shared`.
* Mantener la estructura del monorepo (`scripts/`, `services/`, `uis/`, `packages/shared/`).
* No inventar categorías ni sedes: usar exactamente las definidas en `CONTEXT-company.md`.