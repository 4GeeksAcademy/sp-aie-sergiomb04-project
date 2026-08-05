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
- `POST /auth/change-password`

## Autenticacion

Las rutas sensibles requieren `Authorization: Bearer <token>`.

Variables de entorno soportadas:

- `SECRET_KEY`: clave de firma del JWT
- `ACCESS_TOKEN_EXPIRE_MINUTES`: expiracion del token en minutos
- `TRACKFLOW_SUPPLIERS_DB_PATH`: ruta opcional del TinyDB de proveedores
- `TRACKFLOW_USERS_DB_PATH`: ruta opcional del TinyDB de usuarios/perfiles/auth
- `TRACKFLOW_INCIDENTS_DB_PATH`: ruta opcional del TinyDB de incidencias
- `TRACKFLOW_DB_PATH`: alias legacy (solo suppliers) para compatibilidad hacia atras
- `PASSWORD_RESET_EXPIRE_MINUTES`: expiracion del token de recuperacion
- `PASSWORD_RESET_BASE_URL`: URL base del frontend para construir `/reset-password?token=...`
- `RESEND_API_KEY`: API key del proveedor de correo Resend
- `RESEND_FROM_EMAIL`: remitente verificado en Resend

Ejemplo de configuracion en `services/api/.env.example`.

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
# Analizar CSV
curl -X POST "http://localhost:8000/api/incidents/analyze" \
  -H "Authorization: Bearer <token>" \
  -F "file=@../../scripts/incidents-analysis/incidents-trackflow.csv"

# Exportar ultimo resultado
curl -L "http://localhost:8000/api/incidents/results/export" \
  -H "Authorization: Bearer <token>" \
  -o incidents-analysis-results.csv

# Registrar usuario
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ops@trackflow.test",
    "password": "Secret123",
    "name": "Ops User",
    "phone": "+34 600 000 000",
    "address": "Calle Mayor 1"
  }'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "ops@trackflow.test", "password": "Secret123"}'
```

## Tests

```bash
# Ejecutar tests
uv run pytest

# Ejecutar tests con cobertura
uv run pytest --cov
```

## Notas

- El servicio usa la misma validacion y calculo de metricas del script en `scripts/incidents-analysis/domain`.
- Si no hay analisis previo, el endpoint de export devuelve `404`.
- Gestion de entorno via `uv` — no requiere configuracion adicional de virtualenv.
