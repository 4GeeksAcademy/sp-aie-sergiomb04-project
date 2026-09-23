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

### Implementación de Colas de Mensajes y Tareas Asíncronas con Celery + Redis (Completado)
- Configuración de arquitectura Productor/Consumidor con Celery 5 y Redis como broker y result backend en `services/celery_app.py` y `services/api/trackflow_api/celery_app.py`, habilitando `task_track_started = True`, TTL de resultados a 1 hora y time limits (`task_time_limit=300`, `task_soft_time_limit=240`).
- Infraestructura Docker orquestada en `docker-compose.yml` con servicios `redis` (`redis:alpine`, política `noeviction`, healthcheck activo `redis-cli ping`), `worker` (proceso independiente `celery worker`) y `flower` (dashboard de monitoreo en puerto `5555`).
- Modelo y tabla `dead_letter_queue` implementada con SQLModel para persistencia de fallos definitivos con campos `task_id`, `task_name`, `retry_count`, `error_message`, `payload_ref` y `created_at`.
- Tareas pesadas asíncronas en `trackflow_api/tasks.py` (`execute_weekly_performance_pipeline_task` y `execute_sample_heavy_task`) con payload ligero por referencia, logging estructurado por ciclo, reintento con backoff exponencial (`countdown = 2 ** retries * 5`) y persistencia automática en tabla DLQ al agotar reintentos.
- Endpoints en FastAPI:
  - `POST /reporting/pipeline-runs` y `POST /tasks/pipeline-run`: Respuesta inmediata `202 Accepted` (<200ms) con `task_id` y `status="pending"`.
  - `GET /tasks/{task_id}`: Polling de estado normalizado (`pending`, `started`, `success`, `failure`).
  - `GET /tasks/dlq`: Consulta paginada de registros en Dead Letter Queue.
- Suite de tests unitarios y de integración en `tests/test_celery_tasks.py` cubriendo configuración Celery, encolado, polling, backoff exponencial y guardado en DLQ.

### Modelo de Regresión para Predicción de Ventas / Sales Forecasting (Completado)
- Gestión de entorno configurada con `uv` y dependencias (`pandas`, `numpy`, `scikit-learn`, `xgboost`, `matplotlib`, `scipy`, `pytest`) en `pyproject.toml`.
- Módulo de preparación de datos y split temporal en `src/pipelines/data_prep.py` con división cronológica estricta: 8 años de entrenamiento (96 meses: 2016-2023) y 2 años de prueba (24 meses: 2024-2025), garantizando ausencia total de data leakage y ajuste de transformaciones exclusivamente en train.
- Modelo **Random Forest Regressor** (`random_state=42`, `n_estimators=100`) implementado en `src/pipelines/train_forecast.py` con justificación técnica para Finanzas (explicabilidad por árboles, intervalos de incertidumbre empíricos percentil 5-95 y robustez ante picos estacionales).
- Módulo de métricas de evaluación en `src/pipelines/evaluate.py` calculando explícitamente en el conjunto de test: **MSE** (`13.32B €²`, RMSE `115.4K €` / 8.88% de la media), **PSI** (`5.5268` reflejando crecimiento acumulado de 10 años), **Normalized Gini** (`0.6788` de capacidad de discriminación) y **K2 Score** (`0.5924`, $p=0.7436 > 0.05$ confirmando residuos normales sin sesgo sistemático), junto con **WAPE** (`7.09%`) y reporte exportado a `reports/metrics_report.json`.
- Visualización de alta resolución generada en `reports/figures/sales_forecast_trackflow.png` mostrando ventas reales de los 2 años de prueba, predicciones y banda de variabilidad.
- Suite de pruebas unitarias en `tests/pipelines/test_sales_split.py` pasando al 100% en `pytest` (`uv run pytest tests/pipelines/test_sales_split.py`).
- Documentación completa en `README.md` y checklist de 17 tareas completado en `.tasks/INSTRUCCIONES_AGENTE_TRACKFLOW.md`.

### Evaluación Formal de Modelo de Regresión (Ticket #ML-EVAL-2026-04 - Completado)
- Estrategia de validación cruzada temporal forward-chaining implementada con `TimeSeriesSplit(n_splits=5)` en `src/pipelines/temporal_evaluation.py`, con comprobación algorítmica estricta de no-mezcla y no-barajado (`shuffle=False`).
- Cálculo y reporte de métricas en formato formal `media ± desviación estándar`:
  - **Train MAE:** $13,891.29 \pm 2,335.74$ EUR vs. **Val MAE:** $64,707.41 \pm 24,138.56$ EUR.
  - **Train RMSE:** $17,784.19 \pm 3,076.44$ EUR vs. **Val RMSE:** $77,245.96 \pm 26,433.09$ EUR.
  - Brecha de generalización persistente ($+59,461.77$ EUR RMSE / $+50,816.12$ EUR MAE).
- Visualización dual de curva de aprendizaje en alta resolución generada en `data/eval/learning_curve.png` (RMSE y MAE vs tamaño creciente de entrenamiento: 16 a 80 meses).
- Justificación exhaustiva de negocio para la priorización de **RMSE** frente a MAE, vinculada al riesgo de rotura de capacidad en almacenes de Los Ángeles y Zaragoza y penalizaciones contractuales con marcas B2B.
- Reporte técnico formal emitido en `data/eval/evaluation_report.md` diagnosticando explícitamente **Overfitting (Alta Varianza)** y proponiendo una acción correctiva de regularización de hiperparámetros (`max_depth=5`, `min_samples_leaf=4`, `min_samples_split=6`) e ingeniería de variables autoregresivas (`lag_12_revenue_eur`, `rolling_mean_3m_revenue_eur`).
- Suite de pruebas unitarias en `tests/pipelines/test_temporal_cv.py` (6 tests pasando al 100% en `pytest`, acumulando 12 tests en la suite de pipelines).
- Registro de tareas (16/16) en `.tasks/TASK-regression-model-eval.md` y métricas serializadas en `data/eval/cv_metrics.json`.

### Hito 7 — RAG y Base de Conocimiento (Completado)
- Ingesta de corpus oficial de conocimiento en `docs/company-knowledge-base/` con los 4 documentos corporativos: `trackflow-sla-delivery.es.md`, `trackflow-returns-policy.es.md`, `trackflow-carrier-coverage.es.md` y `trackflow-storage-pricing.es.md`.
- Módulo de preparación e indexación en `data/process/rag.py` con segmentación semántica autocontenida (3 chunks por documento, 12 chunks en total) preservando reglas completas y condiciones contractuales. Inserción idempotente mediante UUIDs deterministas (v5) en la colección Qdrant `trackflow_knowledge` (`Distance.COSINE`).
- Módulo de recuperación y generación en `data/pipelines/rag.py` estructurado en funciones desacopladas:
  - `retrieve()`: Búsqueda vectorial filtrando por umbral de similitud `min_score = 0.35` y retornando payloads limpios.
  - `generate_answer()`: Formulación de respuestas con voz de Account Manager de TrackFlow en llamada comercial y estricto apego al contexto sin alucinaciones (Faithfulness), incorporando las restricciones clave (tiempos +40% en picos de alta demanda, devoluciones internacionales manuales con Sofía Ramos, tarifas de almacenamiento >50 m³ con aprobación de Miguel Torres, excepciones de transportistas con Carlos Vega, y respuesta honesta ante falta de datos).
  - `query()`: Orquestador externo que compone `retrieve()` + `generate_answer()`.
- Servicio de base vectorial **Qdrant** añadido a `docker-compose.yml` (`trackflow-qdrant-dev`, puerto 6333) y variables de entorno documentadas en `.env` y `.env.example`.
- Endpoint REST `POST /knowledge/query` implementado en FastAPI (`services/api/trackflow_api/routes/knowledge.py`) devolviendo `{ "answer": "..." }` sin exponer fragmentos crudos ni puntuaciones al cliente.
- Interfaz web interactiva en Next.js Backoffice (`uis/backoffice/app/(protected)/knowledge/page.tsx`) con preguntas sugeridas de negocio, estados de carga y error, navegación integrada en `ProtectedNavLinks.tsx` y proxy API en `app/api/knowledge/query/route.ts`.
- Suite de pruebas unitarias aisladas con mocks pasando al 100%: 8 tests en `tests/pipelines/test_rag.py` y 3 tests en `services/api/tests/test_knowledge_routes.py`.
- Dataset de evaluación `data/eval/test-queries.json` y script de evaluación `data/eval/eval_retrieval.py` alcanzando un **Recall@3 del 100.00%** (10/10 en posición 1), superando ampliamente el umbral del 80% exigido por `CONTEXT-trackflow.es.md`.
- Documentación técnica formal de arquitectura, estrategia de chunking y prácticas de embeddings en `docs/rag/rag-design.md`.

### Hito 8 — Agente de Soporte con LangGraph (Parte 1 de 2: Migración y Flujo del Agente - Completado)
- Paquete del agente implementado en `services/agent/` desacoplando el flujo RAG en una máquina de estados con LangGraph:
  - `state.py`: Definición de `AgentState` con información mínima y explícita (`question`, `is_valid`, `context`, `answer`, `error`, `trace`), evitando sobrecarga de historial innecesario.
  - `nodes.py`: Nodos con responsabilidad única (`receive_question`, `retrieve_context`, `generate_answer_node`, `handle_no_context`, `handle_error`), reutilizando `retrieve()` y `generate_answer()` de `data/pipelines/rag.py` de forma modular sin invocar el `query()` monolítico.
  - `edges.py`: Aristas condicionales explícitas que enrutan consultas vacías/inválidas a `handle_error` (omitiendo recuperación) y consultas sin contexto sobre el umbral a `handle_no_context` (evitando alucinaciones).
  - `graph.py`: Compilación explícita con `MemorySaver` para checkpointing verificable en cada transición y función de ejecución `run_support_agent()`.
  - `tracing.py`: Gestor y almacén `TraceStore` para auditoría e inspección de traces estructurados por `run_id` y `thread_id`.
- Endpoint REST en FastAPI (`services/api/trackflow_api/routes/agent.py`) montado en `main.py`:
  - `POST /agent/query`: Invocación del agente compilado con validación de entrada y manejo controlado de excepciones (HTTP 400/500) sin filtrar stack traces crudos ni payloads internos.
  - `GET /agent/traces/{run_id}`: Consulta estructurada del trace de ejecución para auditoría y evaluación.
  - `GET /agent/threads/{thread_id}/state`: Inspección del estado guardado en checkpoints por hilo.
- Suite de evals automatizados en `tests/pipelines/test_agent_evals.py` (7 tests pasando al 100%):
  - Verificación del orden estricto de ejecución en el trace (`receive_question` -> `retrieve_context` -> `generate_answer_node`).
  - Validación de desvío por arista condicional ante preguntas vacías (omisión total de `retrieve_context`).
  - Validación de desvío a fallback honesto sin contexto (`handle_no_context`).
  - Anclaje factual estricto en la base de conocimiento de TrackFlow (tarifas de almacenamiento 18 USD / 16 EUR, políticas de devolución internacional manual con Sofía Ramos).
  - Verificación de persistencia de checkpoints e historial de transiciones mediante `thread_id`.
- Tests de endpoints FastAPI en `services/api/tests/test_agent_routes.py` (5 tests pasando al 100%).
- Mantenimiento íntegro de la suite RAG preexistente (8 tests en `tests/pipelines/test_rag.py` pasando al 100%, acumulando 33 tests en `tests/pipelines/`).
- Exportación de trace de muestra en `data/eval/sample_agent_trace.json`.

## Proximos pasos
1. Agente de Soporte Parte 2: Incorporación de herramientas autónomas (tools) y aristas condicionales avanzadas (seguimiento de envíos, consulta de inventario).
2. Estandarizar contratos de tipos compartidos entre app y paquete shared.
3. Avanzar en portal de seguimiento para transportistas y clientes finales.

## Riesgos y foco inmediato
- Riesgo de desalineacion entre contexto TrackFlow y nombre/dominio de la app actual; conviene converger nomenclatura y casos de uso.
- Riesgo de deuda tecnica si se amplia UI sin contratos de datos estables.
- Foco inmediato: mantener consistencia de estado y orquestación resiliente en nuevos pipelines y dashboards.


