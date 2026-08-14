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

### Telemetría TrackFlow — Captura en Frontend y Stub Backend (Completado)
- Endpoint stub `POST /telemetry/events` en FastAPI (`trackflow_api/routes/telemetry.py`) con validación de envelope Pydantic, logging y respuesta 200 OK (`{ "received": N }`).
- Servicio cliente `TelemetryService` en TypeScript (`uis/backoffice/app/services/telemetry.ts`) con buffer/cola local, batch cada 10s/20 eventos, `navigator.sendBeacon` en `visibilitychange`, y reintentos con backoff exponencial.
- `TelemetryProvider` para captura de errores globales no controlados y tracking de navegación en backoffice.
- Instrumentación de eventos de inventario (`inbound_order_created`, `outbound_order_created`, `stock_threshold_triggered`, `outbound_order_rejected_insufficient_stock`, `inventory_form_validation_failed`, `inventory_form_abandoned`), latencia y fallos de API (`api_request_latency_sampled`, `api_request_failed`), y autenticación (`auth_login_succeeded`, `auth_login_failed` con hashing SHA-256 sin PII).
- Tests automatizados en backend (pytest 114 passed) y frontend (jest 25 passed), typecheck y build exitosos.

## Proximos pasos
1. Fase 3 de telemetría: persistencia de eventos en base de datos.
2. Dashboards de operaciones de almacén y reporte ejecutivo sobre datos de telemetría.
3. Estandarizar contratos de tipos compartidos entre app y paquete shared.

## Riesgos y foco inmediato
- Riesgo de desalineacion entre contexto TrackFlow y nombre/dominio de la app actual; conviene converger nomenclatura y casos de uso.
- Riesgo de deuda tecnica si se amplia UI sin contratos de datos estables.
- Foco inmediato: completar Hito 4 con calidad de UX y consistencia de estado para habilitar backend sin retrabajo.