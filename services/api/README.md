# Backend Python unificado

Servicio FastAPI unificado para TrackFlow con dos modulos en un mismo backend:

- Incidencias (`/api/incidents/*`)
- Suppliers (`/suppliers*`)

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
```

## Probar endpoints rapido

```bash
# Analizar CSV
curl -X POST "http://localhost:8000/api/incidents/analyze" \
  -F "file=@../../scripts/incidents-analysis/incidents-trackflow.csv"

# Exportar ultimo resultado
curl -L "http://localhost:8000/api/incidents/results/export" -o incidents-analysis-results.csv
```

## Notas

- El servicio usa la misma validacion y calculo de metricas del script en `scripts/incidents-analysis/domain`.
- Si no hay analisis previo, el endpoint de export devuelve `404`.
- `PIPENV_IGNORE_VIRTUALENVS=1` evita que Pipenv reutilice un entorno activo del shell.
