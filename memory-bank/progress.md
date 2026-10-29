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

### Implementación Completa de Modo Oscuro en UIs (Backoffice & Website - Completado)
- Configuración de selector manual en Tailwind v4 mediante `@variant dark (&:where(.dark, .dark *));` en `uis/backoffice/app/globals.css` y `uis/website/app/globals.css`, evitando que `prefers-color-scheme` sobreescriba la preferencia del usuario.
- Script anti-FOUC en `<head>` para cargar la preferencia `theme` desde `localStorage` sin saltos visuales ni parpadeos.
- Componente `ThemeToggle` reactivo basado en `useSyncExternalStore` para sincronizar `light` / `dark` en toda la aplicación sin advertencias de renderizado en cascada de React 19 / ESLint.
- Cobertura completa de modo oscuro en Website (`uis/website`) y Backoffice (`uis/backoffice`), incluyendo vistas protegidas y componentes internos de:
  - `rfp` (`uis/backoffice/app/(protected)/rfp/page.tsx`): cabeceras, tarjetas de tickets, panel de arbitraje HITL, decisiones departamentales y visor de borradores.
  - `incidents`: paneles de carga y resumen CSV, formulario de registro, filtros y listado de incidencias con badges de estado y sedes.
  - `suppliers`: directorio de proveedores, modal de creación, tabla interactiva, edición rápida de tarifas y estados.
  - `telemetry`: tarjetas KPI de eventos, selectores de rango temporal (24h/7d/30d/personalizado) y tablas métricas de fallos de auth, errores por tipo y latencia por ruta.
  - `reporting`: cuadro ejecutivo de desempeño semanal, filtros por almacén (Los Ángeles / Zaragoza), búsqueda de marcas clientes y tabla detallada con tasas de discrepancia.
  - `knowledge`: corregido título en blanco en modo claro/oscuro alineado al diseño global.
  - `inventory`: soporte completo de modo oscuro en formularios de "Registrar StockEntry" (`StockEntryFormPanel`), "Registrar StockExit" (`StockExitFormPanel`), historial de movimientos (`InventoryOrdersHistoryPanel`), páginas contenedoras y controles asociados (inputs, selects, badges de warehouse/stock, banners de error/éxito y botones de acción).
- Verificación exhaustiva: 27/27 tests Jest pasando y compilación de producción Next.js (`npm run build`) exitosa.

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

### Hito 9 — Agente de Soporte con LangGraph (Parte 2 de 2: Herramientas Fuera del RAG - Completado)
- Paquete de herramientas externas en `services/agent/tools/`:
  - `incidents.py`: Tool tipada de solo lectura para consulta en tiempo real de tickets e incidencias en `get_incidents_db()`. Contratos tipados (`IncidentQueryInput`, `IncidentToolOutput`), extracción automática de identificadores (`TRF-XXXXXX`, UUID, ID numérico), timeout numérico estricto (3.0s) y fallback seguro ante fallos o tickets inexistentes sin inventar estados.
  - `inventory.py`: Tool tipada de solo lectura para verificación de stock de productos en tiempo real (`check_inventory_stock`). Contratos tipados (`InventoryQueryInput`, `InventoryToolOutput`), cálculo de stock en vivo (entradas vs salidas), timeout numérico (3.0s) y fallback controlado ante productos inexistentes o caídas de base de datos.
- Enrutamiento autónomo en `services/agent/edges.py`:
  - `route_after_receive`: Clasificación dinámica de la intención del usuario a partir del contenido de la pregunta sin requerir instrucción explícita del usuario, dirigiendo consultas de tickets a `incident_tool_node`, consultas de inventario a `inventory_tool_node` y consultas de políticas/SLA/procedimientos a `retrieve_context` (RAG).
- Grafo ampliado y compilado en `services/agent/graph.py`:
  - Nuevos nodos con responsabilidad única (`incident_tool_node`, `inventory_tool_node`), transiciones terminales a `END`, preservación de `MemorySaver` para checkpointing y enriquecimiento de trazas con `source_route` y `tool_used`.
- Actualización de API en `services/api/trackflow_api/routes/agent.py`:
  - `POST /agent/query` y `GET /agent/traces/{run_id}` exponen `source_route` y `tool_used`.
- Suite de evals automatizados en `tests/pipelines/test_agent_tools_evals.py` (6 tests pasando al 100%):
  - Enrutamiento autónomo a tool de tickets con reporte de datos reales.
  - Enrutamiento autónomo a RAG con anclaje a base de conocimiento.
  - Enrutamiento autónomo a tool de inventario con existencias en vivo.
  - Fallback honesto ante tickets inexistentes.
  - Fallback defensivo por timeout numérico sin colgar el grafo.
  - Contratos tipados y fallback de inventario.
- Preservación íntegra de suite de pruebas: 39 tests pasando al 100% en `tests/pipelines/` y 5 tests pasando al 100% en `services/api/tests/test_agent_routes.py`.
- Muestras de traces exportadas en `data/eval/sample_agent_ticket_tool_trace.json` y `data/eval/sample_agent_rag_trace.json`.

### Servidor MCP con Autenticación OAuth y Migración del Agente (Completado)
- Servidor MCP implementado bajo `mcps/trackflow_mcp/` usando **FastMCP** y protegido con autenticación OAuth 2.1 / OIDC mediante **MCP Auth** (`mcpauth`).
- Configuración de resource server con endpoints de metadata y discovery:
  - `GET /.well-known/oauth-protected-resource` (RFC 9728 Protected Resource Metadata).
  - `GET /.well-known/oauth-authorization-server` (RFC 8414 Authorization Server Metadata con soporte S256 PKCE).
  - `GET /.well-known/openid-configuration` (OIDC Discovery).
  - `POST /oauth/token` (Endpoint de emisión/intercambio de tokens para testing y MCP Playground).
  - `GET /health` (Healthcheck público).
  - Transmisión por SSE (`/sse`, `/messages`) y Streamable HTTP (`/mcp`).
- Middleware de seguridad `MCPBearerAuthMiddleware` con validación de JWTs Bearer y aplicación del principio de mínimo privilegio mediante scopes:
  - `incidents:read`: Lectura y consulta de incidencias.
  - `incidents:write`: Creación y actualización de estado de incidencias.
  - `inventory:read`: Consulta de inventario y existencias.
- Herramientas MCP expuestas con documentación y esquemas para auto-discovery:
  - `manage_incidents`: Gestión completa de tickets del Incidents Manager (creación con validación de categoría/sede/origen, consulta por ID/CSV ID, y actualización de estado con cumplimiento estricto del ciclo de vida `STATUS_TRANSITIONS`).
  - `query_inventory`: Consulta de solo lectura sobre existencias en almacenes (LA, ZGZ) con cálculo dinámico (entradas - salidas) y **rechazo explícito de cualquier mutación o intento de escritura** (`INVENTORY_MUTATION_FORBIDDEN`).
- Registro de auditoría estructurado en logs (`[MCP_AUDIT]`) por cada invocación (tool, client_id, subject, scopes, resultado, latencia).
- Códigos de error diferenciados para autenticación (`AUTH_401`), autorización (`AUTH_403`), validación (`VALIDATION_ERROR` / `INVALID_STATUS_TRANSITION`) y mutación denegada (`INVENTORY_MUTATION_FORBIDDEN`).
- Migración del agente LangGraph (`services/agent/`):
  - Creación del cliente MCP en `services/agent/mcp_client.py` consumiendo las tools del servidor MCP con token OAuth.
  - Actualización de `incident_tool_node` e `inventory_tool_node` en `services/agent/nodes.py` para invocar exclusivamente el servidor MCP.
  - Deprecación explícita de `services/agent/tools/incidents.py` delegando al cliente MCP para evitar caminos duplicados.
  - Preservación íntegra del enrutamiento autónomo entre RAG y herramientas en `services/agent/edges.py`.
- Suite de pruebas unitarias y de integración en `tests/trackflow_mcp_tests/test_mcp_server.py` validando discovery, auth, scopes, ciclo de vida de tickets, rechazo de escritura y logs de auditoría.

### Hito — Memoria y Auto-mejora de Agentes (Parte 1 de 2: Memoria Persistente y Auto-mejora - Ticket #MEM-092 - Completado)
- **Arquitectura de Memoria Persistente Aislada (`services/agent/memory/`)**:
  - `AgentMemoryStore`: Backend de almacenamiento persistente aislado en SQLite (`data/agent_memory/agent_memory.db`) y snapshots estructurados en JSON (`data/agent_memory/memory_store.json`), completamente desacoplado de las colecciones Qdrant RAG corporativas (`trackflow_knowledge`).
  - Interfaz explícita de lectura/escritura (`read_memories`, `save_approved_memory`, `set_pending_proposal`, `clear_pending_proposal`, `record_audit`) evitando acumulación implícita en el system prompt.
- **Motor de Auto-evaluación y Formulación de Propuestas (`services/agent/memory/evaluator.py`)**:
  - Evaluación determinista de memorabilidad con extracción estructurada (`MemoryProposal`) en el mismo turno de respuesta.
  - Guardrails estrictos de exclusión: bloqueo absoluto de direcciones físicas B2B/B2C, rutas/planos internos de almacén, quejas puntuales de paquetes individuales sin patrón, contratos comerciales activos en negociación (área CRM de Miguel Torres) y tentativas de envenenamiento de memoria.
  - Descarte por defecto de interacciones rutinarias no memorables (consultas de tracking puntuales, saludos/cierres y tareas efímeras de traducción).
  - Emisión de propuesta dentro de la respuesta conversacional (`💡 He detectado una regla operativa... ¿Quieres que recuerde...?`) sin escribir directamente a memoria.
- **Clasificador de Intención de Confirmación y Auditoría (`services/agent/memory/classifier.py`)**:
  - Clasificación de intención del usuario (`APPROVE`, `REJECT`, `EDIT`, `AMBIGUOUS_OR_UNRELATED`) basada en delimitadores de palabras y análisis semántico, evitando matches ingenuos de subcadenas.
  - Restricción estricta de una sola propuesta pendiente a la vez por hilo (`thread_id`).
  - Resolución por defecto: ante silencio, ambigüedad o cambio de tema, la propuesta se descarta automáticamente sin asumir aprobación.
  - Extracción de preguntas encadenadas (`remaining_query`) para responder de forma natural si el usuario aprueba y pregunta algo nuevo en el mismo mensaje.
  - Registro de auditoría inmutable (`MemoryAuditRecord`) en tabla `memory_audit` y archivo `data/agent_memory/audit_log.json` para cada propuesta evaluada (aprobada, rechazada o descartada).
- **Consolidación y Política de Expiración (`services/agent/memory/consolidator.py`)**:
  - Consolidación por `(carrier, country)` para evitar fragmentación en las 8 empresas de transporte de EE. UU. y España.
  - Política de TTL de 7 días para contextos transitorios de incidencias recurrentes (`incident_context`), filtrando entradas obsoletas de la memoria activa.
- **Integración en Grafo LangGraph y API REST**:
  - Integración en nodos `receive_question` (procesamiento prioritario de respuestas a propuestas pendientes), `retrieve_context` (inyección controlada de memorias operativas activas en el contexto del agente), `incident_tool_node`, `inventory_tool_node` y `generate_answer_node`.
  - Endpoints en FastAPI (`services/api/trackflow_api/routes/agent.py`): `GET /agent/memory`, `GET /agent/memory/audit`, `POST /agent/memory/consolidate` y enriquecimiento de `POST /agent/query` con `new_proposal` y `proposal_decision`.
- **Suite de Pruebas y Evals**:
  - 51 tests automatizados en `tests/pipelines/test_agent_memory.py` pasando al 100%, cubriendo aislamiento, guardrails de PII/contratos/envenenamiento, descarte de consultas rutinarias, propuesta en respuesta, unicidad de propuesta pendiente, clasificador de intención, 4 ciclos completos de interacción, consolidación por carrier+país, y expiración TTL.
  - 107 tests totales pasando en la suite completa de `tests/` (`uv run pytest`) y 5 tests pasando en `services/api/tests/test_agent_routes.py`.

### Hito 8 — Aseguramiento de Agentes: Harness y Guardrails (Parte 2 de 2 - Ticket #SEC-114 - Completado)
- **System Prompt Seguro y Aislamiento de Entorno:**
  - Rediseño e implementación del system prompt en `services/agent/prompts.py` y `data/pipelines/rag.py` bajo la identidad del agente de primera línea de CX de Valentina Cruz (CX Manager).
  - Segregación estricta de autoridad: bloque supremo `<<<SYSTEM_INSTRUCTIONS>>>` inmutable frente a `<<<USER_INPUT>>>` y `<<<UNTRUSTED_REFERENCE_DATA>>>`.
  - Definición explícita de dominios: tracking, devoluciones y SLAs segregados estrictamente por país (EE. UU. vs. España), e incidencias operativas.
  - Prohibición explícita de uso como chatbot personal y prohibición estricta de divulgación de datos sensibles (tarifas negociadas con carriers, planos y rutas internas de almacenes, y pedidos de otros clientes).
- **Harness y Guardrails Deterministas (`services/agent/guardrails/`):**
  - `JailbreakSecurityGuard`: Bloqueo determinista ante intentos de omisión de instrucciones, prompts de sin reglas, olvido de identidad empresarial y extracción de system prompt (`FailureType.SECURITY`).
  - `PersonalTaskGuard`: Detección y rechazo de tareas no relacionadas (ensayos, tareas escolares, poemas, código externo, terapia) con mensaje de reconducción al dominio CX (`FailureType.CONTENT`).
  - `CasualScopeGuard`: Detección de saludos, trivia horaria y conceptos generales de logística con respuesta breve y reconducción obligatoria a la operativa de TrackFlow en Los Ángeles y Zaragoza.
  - `SessionOrderAuthGuard`: Control de autorización por sesión (Caso 3 CONTEXT), bloqueando consultas de pedidos ajenos o no autorizados (`FailureType.CONTENT`).
  - `CrossCountryPolicyGuard`: Bloqueo de solicitudes de mezcla de políticas de devolución transfronterizas entre España y Los Ángeles (Caso 4 CONTEXT, `FailureType.CONTENT`).
  - `OutputGuard`: Inspección de salidas previa a la entrega al usuario frente a fallos estructurales (vacío/malformado), filtración de directivas internas y fuga de datos confidenciales de negocio.
  - `Sanitizer`: Aislamiento y neutralización de inyecciones indirectas en fragmentos de RAG y tools mediante tags XML `untrusted_external_content` con `executable="false"`.
- **Integración en LangGraph y API REST:**
  - Incorporación en el grafo de nodos dedicados `guardrail_block_node` y `casual_response_node` con checkpointing en `services/agent/graph.py` y `services/agent/nodes.py`.
  - Enrutamiento autónomo en `services/agent/edges.py` preservando compatibilidad con flujos preexistentes (RAG, external tools y memoria).
  - Bloqueo preventivo de envenenamiento de memoria: si una solicitud es bloqueada por guardrails, se omite cualquier evaluación o consolidación de memoria.
  - Endpoints REST en FastAPI (`services/api/trackflow_api/routes/agent.py`):
    - `POST /agent/query`: Exposición de metadata de guardrails (`guardrail_action`, `guardrail_failure_type`, `guardrail_reason`) y parámetros de autorización de sesión (`session_user`, `authorized_orders`).
    - `GET /agent/guardrails/summary` y `GET /agent/guardrails/metrics`: Reporte de observabilidad con agregados de activaciones por tipo (`ESTRUCTURAL`, `CONTENIDO`, `SEGURIDAD`) y por guardrail.
    - `POST /agent/guardrails/reset`: Endpoint de reinicio para sesiones de test.
  - `tests/pipelines/test_agent_guardrails.py`: Cobertura completa sin dependencia de LLM vivo para system prompt, 5 variantes de jailbreak, abuso de tareas personales, trivia con reconducción, autorización por sesión, políticas transfronterizas, inyección indirecta y output guards.
  - `services/api/tests/test_agent_guardrails_routes.py`: Verificación de endpoints FastAPI, filtros y métricas vía TestClient.
  - Corrección de dependencia circular entre `data/pipelines/rag.py` y `services/agent/prompts.py` desacoplando carga de prompts.
  - Robustecimiento de patrones regex con límites de palabra en `CrossCountryPolicyGuard` y soporte para variantes en español de anulación de reglas y tareas personales.
  - Cobertura global de 132 tests pasando al 100% en la suite completa de `pytest`.

### Hito 9 — Flujos de Trabajo Agénticos: Recepción y Enrutamiento de RFPs (Parte 1 de 3 - Completado)
- **Dependencias e Ingesta Documental (`data/pipelines/rfp_intake/ingestion.py`):**
  - Incorporación de `markitdown[pdf]` y `py-readability-metrics` mediante `uv add`.
  - Conversión de archivos PDF a Markdown con `MarkItDown` (`convert_pdf_to_markdown`) y cálculo de métricas de legibilidad con `py-readability-metrics` (`flesch_kincaid_grade`, `flesch_reading_ease`, `gunning_fog`, `coleman_liau`, `dale_chall`, `ari`, `smog`, `word_count`, `sentence_count`).
  - Extracción estructurada de metadatos de negocio alineada a `CONTEXT-trackflow.es.md`: `client_name`, `client_country` (`Spain` o `USA`), `currency` (`EUR` o `USD`), `services_requested`, `monthly_volume`, `deadline`, `budget_range` y `departments_needed`.
- **Persistencia SQLModel / PostgreSQL (`services/api/trackflow_api/models.py` y `data/pipelines/rfp_intake/persistence.py`):**
  - Nuevas entidades persistidas en base de datos relacional (`RFPTicket` / `Ticket`, `RFPMetadata`, `DepartmentSection`, `RFPFinalDocument`) gestionando el ciclo de vida de la Parte 1 (`analizando`, `descartado`, `analisis_completo`).
- **Grafo Dedicado LangGraph: Orchestrator-Worker-Synthesizer (`data/pipelines/rfp_intake/`):**
  - **Paso 0 (`ingest_document_node`):** Conversión PDF $\rightarrow$ Markdown, métricas de legibilidad y persistencia de `RFPMetadata`.
  - **Nodo 1 (`classifier_node` — Triage Agent):** Clasificación de RFPs formales e informales frente a documentos inválidos (como pitches comerciales de tarifas de transportistas entrantes), marcando `Ticket.status = "descartado"` con motivo explícito sin fallos silenciosos.
  - **Nodo 2 (`orchestrator_node` — Decomposition):** Mapeo de requerimientos hacia los departamentos oficiales de TrackFlow (`warehouse` - Ana Whitfield, `lastmile` - Carlos Vega, `reverse` - Sofía Ramos), respetando exclusiones explícitas de alcance y segmentando extractos relevantes por departamento.
  - **Nodos 3..N (`department_worker_node` — Workers Paralelos con `Send`):** Ejecución en paralelo únicamente para los departamentos requeridos, extrayendo `key_aspects` sin inventar cifras ausentes (registrando `open_questions` cuando faltan pallets, SKUs o volumen mensual) e incorporando las restricciones de cumplimiento (§5).
  - **Nodo 4 (`synthesizer_node` — Synthesizer Agent):** Generación del resumen ejecutivo para Ventas (`"¿Qué pedirle a qué departamento?"` para el equipo de Miguel Torres), contrato estructurado de handoff (`handoff_payload` con `ready_for_part_2 = True`) y transición a `Ticket.status = "analisis_completo"`.
- **Backend FastAPI (`services/api/trackflow_api/routes/rfp.py`) y Backoffice UI (`uis/backoffice/app/(protected)/rfp/page.tsx`):**
  - `POST /api/rfp/upload`: Almacenamiento del PDF en `data/raw/<ticket_id>.pdf`, creación de `Ticket` en estado `analizando`, ejecución asíncrona del grafo con `BackgroundTasks` y respuesta inmediata `HTTP 202 Accepted`.
  - `GET /api/rfp/{ticket_id}` y `GET /api/rfp`: Consulta de estado, metadatos, métricas de legibilidad y desglose por departamento.
  - Interfaz en `uis/backoffice` (`/rfp`) con subida de PDF, polling automático de estados (`analizando` $\rightarrow$ `analisis_completo` / `descartado`), visualización de métricas de legibilidad, síntesis comercial y tarjetas de `key_aspects` por departamento.
- **Datos Semilla, Scripts, Diseño y Pruebas Automatizadas:**
  - PDFs de prueba generados en `rfp-requests/trackflow/` y `docs/milestone-9/rfp-requests/trackflow/` (`trackflow-request-1.pdf` / `CONTEXT-trackflow-request-1.pdf` ModaViva formal, `trackflow-request-2.pdf` / `CONTEXT-trackflow-request-2.pdf` Luna Cosmetics informal, `trackflow-request-3.pdf` / `CONTEXT-trackflow-request-3.pdf` pitch de transportista inválido).
  - Detección y aislamiento de departamentos inexistentes (`unsupported_departments`), pre-validación de conflictos entre workers (`potential_conflicts`: `volume-vs-capacity`, `currency-mismatch`) y manejo anti-zombie en `run_rfp_intake_pipeline`.
  - Documentación completa y respuestas a las 5 Preguntas de Diseño con checklist 32/32 en `docs/milestone-9/README.md`.
  - Script CLI standalone en `scripts/rfp_smoke_test.py`.
  - Suite de pruebas en `tests/pipelines/test_rfp_intake.py` (8 tests) y `services/api/tests/test_rfp_routes.py` (2 tests) pasando al 100%.

### Hito 9 — Flujos de Trabajo Agénticos: Generación de Respuestas a RFPs (Parte 2 de 3 - Completado)
- **Consumo de Handoff sin Re-ingesta de PDF:**
  - Consumo directo del contrato de handoff de la Parte 1 desde PostgreSQL (	icket_id + key_aspects + metadatos compartidos) vía get_rfp_ticket_bundle(ticket_id) sin volver a parsear el archivo PDF original.
- **Generadores por Departamento Activo (data/pipelines/rfp_intake/generators.py):**
  - Generador especializado para warehouse (Ana Whitfield): capacidad de almacenamiento, costos por pallet/SKU, plazo de onboarding de 10 días, SLA de entrega 98.5% y tabla de descuentos por volumen en moneda correspondiente al país.
  - Generador especializado para lastmile (Carlos Vega): opciones de transportistas multicarrier según destino, SLA de entrega del 99.0%, tabla de descuentos por volumen y confidencialidad comercial estricta sin divulgar tarifas internas negociadas con transportistas.
  - Generador especializado para 
everse (Sofía Ramos): operativa integral de retornos, coste por devolución, inspección de calidad, plazo reglamentario de 48 a 72 horas (nunca en menos de 48 horas conforme a §5), SLA del 98.0% y tabla de descuentos por volumen.
- **Evaluadores Concurrentes en Paralelo (data/pipelines/rfp_intake/evaluators.py):**
  - evaluate_readability: validación objetiva con py-readability-metrics (Reading Ease, Flesch-Kincaid, longitud mínima de 50 palabras y oraciones).
  - evaluate_relevance: validación de cobertura de alcance de propuesta y conceptos departamentales.
  - evaluate_compliance: validación algorítmica estricta de las 5 reglas de negocio de §5 (currency_match, delivery_sla_percentage, 
o_returns_under_48h, olume_discount_table, 
o_carrier_negotiated_rates).
  - 
un_parallel_evaluation: orquestación asíncrona concurrente mediante syncio.gather emitiendo el objeto estructurado EvaluationResult.
- **Ciclo Generador-Evaluador y Control de Límite de Iteraciones (data/pipelines/rfp_intake/response_flow.py):**
  - Límite de iteraciones fijado en max_iterations = 3.
  - Ante fallo de evaluación, inyección de feedback concreto y accionable para reintento automático.
  - Si una sección agota el límite sin pasar, se conserva el último borrador generado junto con su EvaluationResult, se marca la sección y el ticket con estado 
eeds_human_review, pasando directamente al handoff de la Parte 3 sin descartar jamás el ticket.
  - Transición de estados en PostgreSQL: nalisis_completo -> generando_borrador -> en_evaluación -> 
eeds_human_review (si agota reintentos) o listo con evaluaciones aprobadas.
- **Integración Backend y Frontend Backoffice:**
  - Endpoint POST /api/rfp/{ticket_id}/generate con soporte asíncrono y síncrono (?sync=true).
  - Proxy Next.js en uis/backoffice/app/api/rfp/[ticketId]/generate/route.ts.
  - Interfaz de Backoffice actualizada (uis/backoffice/app/(protected)/rfp/page.tsx) con botón de disparo, polling en vivo durante generación/evaluación, banner de aviso ante 
eeds_human_review, visor de borradores y tarjetas de auditoría visual para los evaluadores paralelos.
- **Pruebas Automatizadas y Documentación:**
  - 12 pruebas unitarias en 	ests/pipelines/test_rfp_generation.py cubriendo generadores, evaluadores paralelos, fallos genéricos, infracciones de compliance (§5: moneda, devoluciones < 48h, tabla de volumen y tarifas de transportistas) y agotamiento de iteraciones a 
eeds_human_review.
  - 3 pruebas de endpoints en services/api/tests/test_rfp_routes.py (23 pruebas pasando al 100% en la suite de RFP).
  - Documentación completa y respuestas a las 4 Preguntas de Diseño con checklist 23/23 en docs/milestone-9/README_part2.md.

### Hito 9 — Flujos de Trabajo Agénticos: Aprobación y Cierre de RFPs (Parte 3 de 3 - Completado)
- **Aprobación Humana Aislada (HITL) con interrupt():**
  - Implementación de compuertas de interrupción explícitas (interrupt()) antes del sign-off de cada departamento activo en data/pipelines/rfp_intake/approval_flow.py.
  - Aislamiento total de ramas por namespace de hilo (
fp-{ticket_id}:{department_id}) permitiendo que departamentos avancen y aprueben en paralelo sin bloquear a los demás.
  - Checkpointer persistente SqliteSaver (data/checkpoints/rfp_approval.db) para checkpointing de estado e historial.
  - Reanudación validada mediante Command(resume=...) aceptando pprove, 
eject y 
equest_changes.
- **Arbitraje de Conflictos y Trazabilidad (§7 BRIEFING):**
  - Nodo de arbitraje determinista en data/pipelines/rfp_intake/arbitration.py respondiendo a los 3 triggers del BRIEFING: olume-vs-capacity, 
eturns-sla-breach y currency-mismatch.
  - Asignación estricta de árbitros fijos humanos (Miguel Torres para capacidad y divisas; Sofía Ramos para devoluciones) sin consenso estocástico de LLMs.
  - Registro de trazas de auditoría (TraceStep) con agente, input, output y timestamp ISO UTC.
  - Límite de iteraciones fijado en 3 para evitar bucles indefinidos de cambios.
- **Síntesis del Documento Final y Estados del Ciclo de Vida:**
  - Consolidación automática de extractos aprobados, resumen comercial y sign-off formal en RFPFinalDocument (tabla 
fp_final_documents).
  - Ciclo de estados: esperando_aprobación durante la revisión humana -> 	erminado con documento persistido.
- **Backoffice UI y Endpoints API:**
  - Endpoints REST en FastAPI: POST /api/rfp/{ticket_id}/approval/initiate, POST /api/rfp/{ticket_id}/approval/{department_id}, GET /api/rfp/{ticket_id}/final-document, POST /api/rfp/{ticket_id}/arbitrate.
  - Proxies Next.js en uis/backoffice/app/api/rfp/.
  - UI interactiva en Backoffice con paneles de sign-off departamental (Aprobar, Solicitar Cambios, Rechazar), panel de verificación de arbitraje y visor oficial del documento final consolidado.
- **Suite de Pruebas Completa (30 tests pasando al 100%):**
  - 7 pruebas en 	ests/pipelines/test_rfp_approval.py (interrupción, reanudación, paralelismo entre departamentos, 3 triggers de arbitraje y prueba E2E de punta a punta desde Parte 1 hasta Parte 3).
  - 3 pruebas de integración de endpoints en services/api/tests/test_rfp_routes.py.
  - Documentación completa en docs/milestone-9/README_part3.md.

### Modo Oscuro en UIs (Backoffice y Website) y Corrección de Título en /knowledge (En curso en `feat/uis-dark-mode`)
- **Corrección de título en `/knowledge`**:
  - Homogeneizado el estilo tipográfico del título a `text-2xl font-semibold tracking-tight text-slate-950 dark:text-white` alineándolo con el resto de secciones operativas como `/products` (`InventoryProductsPanel.tsx`).
  - Configurado el selector explícito `@variant dark (&:where(.dark, .dark *));` en Tailwind CSS v4 para evitar que la preferencia del sistema operativo (`prefers-color-scheme: dark`) aplique clases `dark:` sobre fondos claros si el modo oscuro no ha sido activado explícitamente.
- **Implementación de Dark Mode en Backoffice y Website**:
  - Soporte de variante `dark:` por clase en `uis/backoffice/app/globals.css` y `uis/website/app/globals.css`.
  - Componente accesible `ThemeToggle` (`useSyncExternalStore` con `MutationObserver`) para alternar temas sin parpadeos ni problemas de renderizado de React 19.
  - Script anti-FOUC en `<head>` para persistir la preferencia en `localStorage` (`trackflow_theme`) y aplicarla inmediatamente antes de la hidratación.
  - Integración en cabeceras de navegación (`ProtectedNavLinks`, `layout.tsx` en Backoffice y `Navbar.tsx` en Website), páginas públicas (`/login`, `/register`, `/forgot-password`, `/reset-password`) y secciones clave (`/products`, `/knowledge`, `/application`, etc.).
  - Verificación exitosa de compilación (`next build`) y pruebas (`jest`) en ambas aplicaciones.

### Corrección de Aprobaciones Departamentales (HITL) en Propuestas Económicas de RFPs (Completado)
- **Diagnóstico de causa raíz del error HTTP 500**:
  - En entornos Dockerizados con bind mounts de host, `sqlite3.connect` y `SqliteSaver.setup()` lanzaban `sqlite3.OperationalError: unable to open database file` al intentar abrir de forma bloqueada el archivo `rfp_approval.db`.
  - La restricción de versión `langgraph-checkpoint-sqlite<3` en `services/requirements.txt` (2.0.10) presentaba incompatibilidad de serialización (`AttributeError: 'JsonPlusSerializer' object has no attribute 'dumps'`) con `langgraph-checkpoint>=4.3.0`.
- **Implementación resiliente del Checkpointer en `data/pipelines/rfp_intake/approval_flow.py`**:
  - Mecanismo multiruta en `get_default_checkpointer()`: evalúa variable de entorno `RFP_APPROVAL_DB_PATH`, candidatos en `data/checkpoints/rfp_checkpoints.sqlite`, `data/checkpoints/rfp_approval.db`, `/tmp/rfp_checkpoints.sqlite` y fallback automático y seguro a `MemorySaver` en memoria ante cualquier fallo de sistema de archivos o lock.
  - Implementación singleton de `_default_checkpointer` evitando reapertura continua de conexiones SQLite y reejecución redundante de scripts DDL.
  - Actualización de dependencia en `services/requirements.txt` a `langgraph-checkpoint-sqlite>=3.1.2`, alineada con `services/api/pyproject.toml`.
- **Mejora en UX y Manejo de Errores en Backoffice UI (`uis/backoffice/app/(protected)/rfp/page.tsx`)**:
  - Incorporación de estado `approvalError` con banner de error visible y descartable en la interfaz para acciones de "Aprobar", "Solicitar Cambios" y "Rechazar", evitando fallos silenciosos ante problemas de red o backend.
  - Tipado estricto en interfaces de arbitraje (`ArbitrationResponse`, `ArbitrationResolution`) eliminando tipos `any` y warnings de React 19 / ESLint.
- **Verificación Exhaustiva**:
  - Validación E2E mediante invocaciones reales HTTP POST vía port 5001 y port 8000 para "approve", "request_changes" y "reject" confirmando respuestas HTTP 200 OK y transición de tickets a `esperando_aprobación` y `terminado` con `RFPFinalDocument` sintetizado.
  - 30/30 tests automatizados de backend pasando al 100% (`pytest`).
  - 27/27 tests de frontend pasando (`jest`), ESLint sin errores ni warnings y compilación de producción Next.js (`npm run build`) exitosa.

### Corrección de Rutas Proxy del Frontend hacia Backend Python (ix/frontend-api-routes - Completado)
- **Diagnóstico de causa raíz en actualización de estado de incidencias (PATCH /api/incidents/[id]/status)**:
  - En uis/backoffice/app/api/incidents/[id]/status/route.ts, getAuthorizedSessionHeaders() se invocaba sin { "Content-Type": "application/json" }. Al enviar ody: JSON.stringify(body) con Node etch, la cabecera por defecto Content-Type: text/plain;charset=UTF-8 provocaba que FastAPI (patch_incident_status) no parseara el cuerpo como JSON y lanzara RequestValidationError HTTP 400 ("Input should be a valid dictionary or object to extract fields from").
- **Corrección y estandarización de rutas proxy en uis/backoffice**:
  - uis/backoffice/app/api/incidents/[id]/status/route.ts: Añadido { "Content-Type": "application/json" } en getAuthorizedSessionHeaders y encodeURIComponent(id).
  - uis/backoffice/app/api/incidents/route.ts y uis/backoffice/app/api/incidents/[id]/route.ts: Estandarizado el envío de cabeceras autenticadas con Content-Type: application/json en POST y codificación segura de id.
  - uis/backoffice/app/api/telemetry/events/route.ts y uis/backoffice/app/services/telemetry.ts: Creada ruta proxy /api/telemetry/events hacia /telemetry/events del backend Python, evitando fallos de conexión directa a localhost:8000 desde el navegador en despliegues contenedorizados.
- **Sincronización reactiva de interfaz en /incidents**:
  - Eventos 	rackflow:incidents-updated emitidos en IncidentRegistrationForm.tsx e IncidentList.tsx y suscritos en IncidentList.tsx e IncidentSummaryPanel.tsx para refrescar listado y métricas al crear o actualizar incidencias sin recargar la página.
- **Verificación**:
  - Nuevos tests unitarios en uis/backoffice/__tests__/incident-routes.test.ts validando cabeceras Content-Type: application/json y Authorization (6 suites / 39 tests pasando en Jest, ESLint limpio sin errores).

## Proximos pasos
1. Pasar a producción el flujo agéntico completo de RFPs en TrackFlow Tech tras revisión con los directores de departamento (Miguel Torres, Ana Whitfield, Carlos Vega, Sofía Ramos).
2. Integrar el pipeline con el sistema de mensajería/email saliente para el envío automatizado de la propuesta económica final a los clientes potenciales.

## Riesgos y foco inmediato
- Riesgo de desalineacion entre contexto TrackFlow y nombre/dominio de la app actual; conviene converger nomenclatura y casos de uso.
- Riesgo de deuda tecnica si se amplia UI sin contratos de datos estables.
- Foco inmediato: mantener consistencia de estado y orquestación resiliente en nuevos pipelines y dashboards.
