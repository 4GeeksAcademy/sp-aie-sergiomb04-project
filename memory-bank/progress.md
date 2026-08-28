# Progress Report - TrackFlow Project

## Estado actual del proyecto
El repositorio ya supero la fase de plantilla y tiene entregables funcionales en frontend y programacion, ademas de una aplicacion Next.js en desarrollo activo para el hito actual.

Estado general: en ejecucion de Hito 4 (Next.js), con base previa establecida en Hitos 1-3.

## Hitos completados

### Hito 1 - Web
- Sitio web corporativo inicial alineado al contexto TrackFlow.
- Landing y propuesta de valor disponibles en index.html.
- Formulario de solicitud en application.html.
- Elementos basicos de accesibilidad y metadata estructurada (schema.org).

### Hito 2 - Programacion
- Logica de dominio implementada en TypeScript bajo src/ (busqueda, validaciones, transformaciones, colecciones).
- Modelos tipados para entidades logisticas (producto, envio, carrier).
- Funciones de scoring y seleccion de transportista, calculos operativos y utilidades de validacion.

### Hito 3 - UI con IA
- Base de interfaces y componentes con apoyo de generacion asistida (enfoque IA-first del track).
- Consolidacion de experiencia UI con Tailwind y componentes reutilizables.
- Preparacion del salto a app estructurada en Next.js para evolucion funcional.

## Trabajo en curso y recientes entregables

### Telemetría TrackFlow — Pipeline de Análisis y Endpoint de Reporte (Completado)
- Módulo analítico en `services/telemetry/analysis.py` (y `trackflow_api/telemetry/analysis.py`) con 4 funciones operacionales vectorizadas en Pandas: `events_per_day`, `error_rate_by_type`, `auth_failure_rate` y `latency_by_route`.
- Filtrado temporal SQL estricto en UTC (`timestamp >= :start AND timestamp < :end`) y extracción de dimensiones desde tags.
- Endpoint `GET /telemetry/report` en FastAPI con resolución de período por defecto a 7 días y caché en memoria con TTL de 60 segundos basada en ventana temporal (`api_cache`).
- Dashboard técnico en Backoffice Next.js (`/telemetry`) consumiendo el endpoint a través del proxy `/api/telemetry/report`, con soporte para rangos rápidos (24h, 7d, 30d), filtros personalizados y métricas operacionales detalladas.
- Cobertura de tests automatizados completa (125 tests en backend con `pytest`, 27 tests en frontend con `jest`, ESLint sin errores y compilación `next build` exitosa).

### Diseño de Data Pipeline de Desempeño de Negocio (Parte 1 de 3 - Completado)
- Documento de diseño técnico y de negocio en `data/pipelines/PIPELINE_DESIGN.md` alineado con `CONTEXT-empresa.md`.
- Identificación y cierre de brecha entre telemetría técnica de ingeniería y reportes ejecutivos/operacionales para Thomas Harry (CEO) y Ana Whitfield (Head of Warehouse Operations).
- Especificación completa de agregación para tabla destino `reporting.weekly_warehouse_client_performance` (grano semanal por almacén y cliente) cubriendo volumen de entrada, throughput de salida, quiebres de stock y tasa de discrepancia.
- Estrategia de idempotencia basada en constraint `UNIQUE (warehouse, client_id, week_start)` y UPSERT atómico, gestión de eventos tardíos (late-arriving data) y deduplicación.
- Esquema de auditoría en `reporting.pipeline_runs` y mapeo a flujos/tareas de Prefect con desacoplamiento en 3 capas (`data/pipelines/`, `data/process/`, `services/reporting/`).

### Pipeline de Desempeño de Negocio Resiliente (Parte 2 de 3 - Completado)
- Flujo principal en Prefect 3 (`weekly_warehouse_client_performance_flow`) y tareas modulares para extracción con retries (`extract_telemetry_events`), transformación con caché de 15 minutos (`transform_warehouse_client_metrics`), carga idempotente con UPSERT atómico (`load_reporting_metrics`) y aislamiento de pasos no críticos con `return_state=True` (`optional_pipeline_notification`).
- Lógica analítica pura y vectorizada en Pandas dentro de `data/process/weekly_performance.py` para métricas semanales: `inbound_units_count`, `outbound_orders_count`, `stockout_events_count`, `discrepancy_events_count` y `discrepancy_rate` (con división segura).
- Modelos ORM SQLModel para `WeeklyWarehouseClientPerformance` (constraint único `uq_weekly_warehouse_client`) y `PipelineRunRecord` para auditoría y observabilidad.
- Soporte para ejecución por script CLI (`python data/pipelines/pipeline.py`) con parámetros configurables de semana.
- 3 endpoints REST en FastAPI bajo `/reporting`:
  1. `GET /reporting/pipeline-runs/latest`: Estado y metadata de la última ejecución.
  2. `POST /reporting/pipeline-runs`: Disparo manual del flow del pipeline.
  3. `GET /reporting/weekly-warehouse-client-performance`: Consulta filtrada de KPIs por semana, almacén y cliente.
- Cobertura de tests automatizados completa (132 tests pasando en `pytest` cubriendo lógica de negocio, flujo Prefect, idempotencia y endpoints API).

### Pipeline de Desempeño de Negocio a Producción (Parte 3 de 3 - Completado)
- Refactorización modular en Prefect 3 con subflows independientes tipados (`extract_telemetry_events_flow`, `transform_warehouse_client_metrics_flow`, `load_reporting_metrics_flow`, `optional_notification_subflow`) orquestados secuencialmente por `weekly_warehouse_client_performance_flow`.
- Suite completa de tests unitarios aislados en memoria (`tests/pipelines/test_pipeline.py`) cubriendo 6 casos de prueba (100% de éxito): validación aislada de cada KPI (`inbound_units_count`, `outbound_orders_count`, `stockout_events_count`, `discrepancy_events_count`, `discrepancy_rate`), pruebas defensivas contra datos malformados/nulos/NaNs y validación contra cálculos matemáticos teóricos.
- Preservación y verificación de ejecución CLI (`python data/pipelines/pipeline.py`) retornando código 0 y JSON estructurado.
- Dashboard Ejecutivo y Operacional en Backoffice Next.js (`/reporting`) consumiendo endpoints de reporting a través de proxies `/api/reporting/...`, con filtros por almacén (Los Ángeles, Zaragoza), marca cliente y semana, resumen de métricas, desglose tabular con badges de estado y control para recálculo manual.
- Inmutabilidad estricta de `telemetry_events` y `services/telemetry/analysis.py`.

### Script Nocturno de Telemetría y Control de Ejecución (Ticket #DEV-53 - Completado)
- Tabla `job_runs` implementada con SQLModel con índice `(job_name, target_date)`, columnas para control de estado (`pending`, `processing`, `completed`, `failed`), timestamps en UTC y registro de mensajes de excepción.
- Servicio `services/job_runner.py` (y `trackflow_api/job_runner.py`) implementando distributed lock nativo (`has_processing_lock`), validación de idempotencia (`has_completed_for_date`), creación de registros y transiciones de estado seguras (`mark_as_completed`, `mark_as_failed`).
- Script CLI aislado `scripts/nightly_export.py` con resolución configurable de `target_date`, validaciones previas de lock/idempotencia, exportación de snapshot backup en CSV (`data/raw/telemetry_YYYY-MM-DD.csv`), disparo de subproceso de pipeline desacoplado y garantía anti-zombie con bloque `try/except/finally`.
- Entrypoint CLI `data/pipelines/telemetry_kpi_daily/run.py` para procesamiento de telemetría diario con soporte `--no-prefect`.
- Cobertura de tests automatizados completa (142 tests backend pasando en `pytest`, incluyendo 10 tests específicos para ciclo de vida, distributed lock, idempotencia y anti-zombie en `services/api/tests/test_nightly_telemetry.py`).
- Generado archivo `.tasks/PullRequest.md` con especificación de PR, configuración de cron (`0 2 * * *`), logs de muestra y formato de exportación CSV.

## Proximos pasos
1. Integración de agentes IA para análisis de anomalías en inventario y recomendaciones logísticas.
2. Estandarizar contratos de tipos compartidos entre app y paquete shared.
3. Avanzar en portal de seguimiento para transportistas y clientes finales.

## Riesgos y foco inmediato
- Riesgo de desalineacion entre contexto TrackFlow y nombre/dominio de la app actual; conviene converger nomenclatura y casos de uso.
- Riesgo de deuda tecnica si se amplia UI sin contratos de datos estables.
- Foco inmediato: mantener consistencia de estado y orquestación resiliente en nuevos pipelines y dashboards.
