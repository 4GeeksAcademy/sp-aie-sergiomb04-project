# Pull Request: Refactorización a Subflows de Prefect 3, Suite de Tests Unitarios y Dashboard de Negocio

## 📌 Resumen Ejecutivo
Este PR completa la **Parte 3** del Hito de Data Pipeline en TrackFlow, llevando a producción el pipeline de desempeño operacional y de negocio para Thomas Harry (CEO) y Ana Whitfield (Head of Warehouse Operations). 

Se refactorizó el pipeline orquestador a **subflows tipados e independientes en Prefect 3**, se implementó una **suite completa de tests unitarios aislados en memoria** (`tests/pipelines/test_pipeline.py`) que valida con 100% de éxito cada KPI y caso defensivo, se aseguró la **compatibilidad y ejecución CLI**, y se integró el **Dashboard Ejecutivo y Operacional** en `uis/backoffice/` consumiendo los endpoints de reporting.

---

## 🛠️ Cambios Implementados

### 1. Refactorización a Subflows en Prefect 3 (`data/pipelines/pipeline.py`)
- **Subflow de Extracción (`extract_telemetry_events_flow`)**: Extracción de eventos de solo lectura desde `telemetry_events` con reintentos configurables (3 retries, 5s delay).
- **Subflow de Transformación (`transform_warehouse_client_metrics_flow`)**: Transformación puramente vectorizada en Pandas con caché de 15 minutos basada en hash del dataset y ventana temporal.
- **Subflow de Carga (`load_reporting_metrics_flow`)**: Inserción atómica idempotente mediante `UPSERT` (`ON CONFLICT (warehouse, client_id, week_start) DO UPDATE`) en `reporting.weekly_warehouse_client_performance`.
- **Subflow de Notificación Aislado (`optional_notification_subflow`)**: Paso no crítico encapsulado con `return_state=True` para prevenir fallos en la orquestación principal ante incidencias externas.
- **Flujo Orquestador Principal (`weekly_warehouse_client_performance_flow`)**: Orquestación secuencial limpia sin estado ni variables globales compartidas.
- **Entrada CLI Preservada**: Entrypoint `if __name__ == "__main__":` con parámetros `--week-start` y `--triggered-by`.

### 2. Suite de Tests Unitarios (`tests/pipelines/test_pipeline.py`)
- **Aislamiento Total (0 Dependencias Externas)**: Pruebas ejecutadas 100% en memoria con fixtures basados en el dominio de TrackFlow.
- **Validación Aislada de KPIs**:
  - `test_kpi1_inbound_units_count`: Validación de suma de volumen entrante (`inbound_order_created`).
  - `test_kpi2_outbound_orders_count`: Validación de conteo de órdenes despachadas (`outbound_order_created`).
  - `test_kpi3_stockout_discrepancies_and_rate`: Validación de alertas de quiebre de stock, discrepancias físicas y tasa calculada.
- **Pruebas Defensivas (`test_defensive_data_handling`)**: Manejo seguro de entradas vacías, tags malformados, valores no numéricos, nulos/NaNs y división segura por cero (`outbound_orders_count == 0`).
- **Validación Matemática Teórica (`test_mathematical_validation_hand_calculated`)**: Validación contra valores teóricos calculados manualmente.
- **Validación de Subflows (`test_subflows_in_isolation`)**: Ejecución de subflows en memoria.

### 3. Dashboard Ejecutivo y Operacional en Backoffice (`uis/backoffice/`)
- **Vista Interactiva (`uis/backoffice/app/(protected)/reporting/page.tsx`)**:
  - Resumen de 5 KPIs operacionales: Unidades Entrantes, Órdenes Despachadas, Alertas de Stock Bajo, Discrepancias Físicas y Tasa Global de Discrepancia.
  - Filtros dinámicos por Almacén (🇺🇸 Los Ángeles, 🇪🇸 Zaragoza, Todos), Marca Cliente y Semana (Lunes a Domingo).
  - Tabla de desglose por almacén y marca cliente con badges de estado.
  - Widget de estado del pipeline con métricas de última corrida (duración, registros extraídos y cargados) y botón para disparar recálculo manual.
- **Proxies API en Next.js**:
  - `GET /api/reporting/weekly-warehouse-client-performance`: Proxy autenticado hacia el endpoint FastAPI.
  - `GET & POST /api/reporting/pipeline-runs`: Proxy para consulta de estado y disparo manual.
- **Navegación**: Enlace agregado en `ProtectedNavLinks.tsx`.

### 4. Documentación y Memoria
- Actualización de `data/pipelines/PIPELINE_DESIGN.md` con la arquitectura de subflows de la Parte 3.
- Actualización de `memory-bank/progress.md`.

---

## 🔒 Cumplimiento de Reglas de Oro e Inmutabilidad
- `telemetry_events` y `services/telemetry/analysis.py` no sufrieron ninguna modificación (inmutabilidad técnica garantizada).
- Todos los nombres y KPIs utilizan la nomenclatura exacta del negocio (`CONTEXT.md`).
- Todas las dependencias son gestionadas limpiamente con `uv` y `npm`.

---

## ✅ Verificación y Pruebas Realizadas
- `python -m pytest tests/pipelines/test_pipeline.py`: 6/6 tests pasando (100% éxito).
- `python -m pytest services/api/tests/test_reporting_pipeline.py`: 7/7 tests pasando (100% éxito).
- `python data/pipelines/pipeline.py --triggered-by cli_test`: Ejecución CLI exitosa con código 0 y salida JSON formateada.
- `npm run lint` & `npm run build` en `uis/backoffice`: Compilación y tipado válidos.
