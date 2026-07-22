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
- `TRACKFLOW_DB_PATH`: ruta opcional para cambiar el archivo TinyDB
- `PASSWORD_RESET_EXPIRE_MINUTES`: expiracion del token de recuperacion
- `PASSWORD_RESET_BASE_URL`: URL base del frontend para construir `/reset-password?token=...`
- `RESEND_API_KEY`: API key del proveedor de correo Resend
- `RESEND_FROM_EMAIL`: remitente verificado en Resend

Ejemplo de configuracion en `services/api/.env.example`.

## Ejecutar con Pipenv

```bash
cd services/api
PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv sync --dev
PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv run dev
```

El servicio quedara disponible en `http://localhost:8000`.

## Comandos utiles

```bash
# Levantar en modo desarrollo (reload)
PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv run dev

# Levantar en modo normal
PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv run start

# Ejecutar un comando Python dentro del entorno
PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv run python -c "from trackflow_api.main import app; print(app.title)"

# Ejecutar seeder de suppliers
PIPENV_IGNORE_VIRTUALENVS=1 PIPENV_VENV_IN_PROJECT=1 pipenv run python -m trackflow_api.seed

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

## Notas

- El servicio usa la misma validacion y calculo de metricas del script en `scripts/incidents-analysis/domain`.
- Si no hay analisis previo, el endpoint de export devuelve `404`.
- `PIPENV_IGNORE_VIRTUALENVS=1` evita que Pipenv reutilice un entorno activo del shell.
