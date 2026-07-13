# Incidents Analysis Script

Herramienta CLI para analizar el CSV de incidencias de TrackFlow y generar resumenes reutilizables por API y backoffice.

## Requisitos

- Python 3.10+
- Archivo CSV UTF-8 con encabezados requeridos

## Uso basico

```bash
cd scripts/incidents-analysis
python3 analyze.py incidents-trackflow.csv
```

## Modos disponibles

```bash
# Salida JSON
python3 analyze.py incidents-trackflow.csv --json --no-prompt

# Exportacion directa a CSV
python3 analyze.py incidents-trackflow.csv --export-path incidents-analysis-results.csv --no-prompt

# Verificacion exacta contra valores esperados del CONTEXT-company.md
python3 analyze.py incidents-trackflow.csv --verify-context
```

Si la verificacion coincide, imprime `CONTEXT VALIDATION: PASS` y sale con codigo `0`.
Si hay diferencias, imprime `CONTEXT VALIDATION: FAIL`, lista los desajustes y sale con codigo `2`.
