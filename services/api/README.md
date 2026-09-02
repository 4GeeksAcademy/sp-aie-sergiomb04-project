# Backend Python unificado

Servicio FastAPI unificado para TrackFlow con dos modulos en un mismo backend:

- Incidencias (`/api/incidents/*`)
- Suppliers (`/suppliers*`)
- Usuarios (`/users*`)
- Perfiles (`/profiles*`)
- Autenticacion JWT (`/auth*`)

## Endpoints

- `POST /api/incidents/analyze`
  - Entrada: `multipart/form-data` con `file`
  - Salida: resumen JSON del analisis
- `GET /api/incidents/results/export`
  - Salida: CSV descargable del ultimo analisis ejecutado
- `POST /suppliers`
- `GET /suppliers`
- `GET /suppliers/{id}`
- `PATCH /suppliers/{id}/rate`
- `PATCH /suppliers/{id}/status`
- `DELETE /suppliers/{id}`
- `POST /users`
- `GET /users`
- `GET /users/{id}`
- `PUT /users/{id}`
- `DELETE /users/{id}`
- `GET /profiles/me`
- `PUT /profiles/me`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /reporting/pipeline-runs` (despacho asíncrono con `202 Accepted` por defecto)
- `GET /tasks/{task_id}` (polling de estado normalizado)
- `POST /tasks/pipeline-run` (disparo asíncrono de pipeline)
- `GET /tasks/dlq` (consulta de Dead Letter Queue de tareas fallidas)

## Autenticacion

Las rutas sensibles requieren `Authorization: Bearer <token>`.

Variables de entorno soportadas:

- `SECRET_KEY`: clave de firma del JWT
- `ACCESS_TOKEN_EXPIRE_MINUTES`: expiracion del token en minutos
- `REDIS_URL`: URL de conexión a Redis para Celery (por defecto `redis://localhost:6379/0`)
- `TRACKFLOW_SUPPLIERS_DB_PATH`: ruta opcional del TinyDB de proveedores
- `TRACKFLOW_USERS_DB_PATH`: ruta opcional del TinyDB de usuarios/perfiles/auth
- `TRACKFLOW_INCIDENTS_DB_PATH`: ruta opcional del TinyDB de incidencias
- `TRACKFLOW_DB_PATH`: alias legacy (solo suppliers) para compatibilidad hacia atras
- `PASSWORD_RESET_EXPIRE_MINUTES`: expiracion del token de recuperacion
- `PASSWORD_RESET_BASE_URL`: URL base del frontend para construir `/reset-password?token=...`
- `RESEND_API_KEY`: API key del proveedor de correo Resend
- `RESEND_FROM_EMAIL`: remitente verificado en Resend

Ejemplo de configuracion en `services/api/.env.example`.

## Celery, Redis & Flower

### Levantar Infraestructura con Docker Compose
```bash
# Levantar Redis, Worker y Flower junto a los servicios
docker compose up -d redis worker flower services

# Ver logs del worker
docker compose logs -f worker

# Acceder al panel de monitoreo Flower
# URL: http://localhost:5555
```

### Ejecutar Worker localmente en desarrollo
```bash
cd services/api

# Iniciar Celery Worker
uv run celery -A trackflow_api.celery_app worker --loglevel=info

# Iniciar Flower (Dashboard de monitoreo)
uv run celery -A trackflow_api.celery_app flower --port=5555
```

### Detener Worker
- En terminal local: `Ctrl + C` (o `SIGINT`/`SIGTERM` para apagado graceful).
- En Docker: `docker compose stop worker flower redis`.

## Ejecutar con uv

```bash
cd services/api
uv sync
uv run uvicorn trackflow_api.main:app --reload --host 0.0.0.0 --port 8000
```

El servicio quedara disponible en `http://localhost:8000`.

## Comandos utiles

```bash
# Levantar en modo desarrollo (reload)
uv run uvicorn trackflow_api.main:app --reload --host 0.0.0.0 --port 8000

# Levantar en modo normal
uv run uvicorn trackflow_api.main:app --host 0.0.0.0 --port 8000

# Ejecutar un comando Python dentro del entorno
uv run python -c "from trackflow_api.main import app; print(app.title)"

# Ejecutar seeder de suppliers
uv run python -m trackflow_api.seed

# Crear un usuario (si faltan argumentos, se pediran por terminal)
uv run create-user \
  --email ops@trackflow.test \
  --password NewSecret123 \
  --name "Ops User" \
  --phone "+34 600 000 001" \
  --address "Avenida Central 10" \
  --role admin \
  --update-existing \
  --reset-password

# Modo totalmente interactivo
uv run create-user
```

## Probar endpoints rapido

```bash
# Disparar tarea asíncrona de reporte de pipeline
curl -X POST "http://localhost:8000/reporting/pipeline-runs" \
  -H "Content-Type: application/json" \
  -d '{"target_week_start": "2026-08-17", "force_recompute": false}'
# Respuesta 202: {"task_id":"...","status":"pending","message":"Task accepted and queued for background processing"}

# Consultar estado de tarea (Polling)
curl "http://localhost:8000/tasks/<task_id>"
# Respuesta 200: {"task_id":"...","status":"success","result":{...},"error":null}

# Consultar Dead Letter Queue (DLQ)
curl "http://localhost:8000/tasks/dlq"
```

## Tests

```bash
# Ejecutar tests
uv run pytest

# Ejecutar tests con cobertura
uv run pytest --cov
```
