# Backend Python de incidencias

Servicio FastAPI para analizar ficheros CSV de incidencias reutilizando la logica del script en `scripts/incidents-analysis`.

## Endpoints

- `POST /api/incidents/analyze`
  - Entrada: `multipart/form-data` con `file`
  - Salida: resumen JSON del analisis
- `GET /api/incidents/results/export`
  - Salida: CSV descargable del ultimo analisis ejecutado

## Ejecutar localmente

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn incidents_api.app:app --reload --host 0.0.0.0 --port 8000
```

## Notas

- El servicio usa la misma validacion y calculo de metricas del script en `scripts/incidents-analysis/domain`.
- Si no hay analisis previo, el endpoint de export devuelve `404`.
