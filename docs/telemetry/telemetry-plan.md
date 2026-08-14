# Plan de Telemetria de TrackFlow

## 1) Alcance y restricciones
- Este entregable define un plan de eventos y esquemas para inventario y backoffice.
- Solo documentacion: no se modifica servidor, endpoints ni instrumentacion.
- Fuente de verdad obligatoria: [.tasks/CONTEXT-empresa.md](.tasks/CONTEXT-empresa.md).
- No se capturan contrasenas, tokens, secretos, cookies de autenticacion, payloads completos ni datos de destinatario final.

## 2) Extraccion literal del contexto de negocio

### Entidades obligatorias
- Product
- InboundOrder
- OutboundOrder
- warehouse
- client

### Restricciones obligatorias
- El stock nunca se modifica directamente: toda modificacion pasa por InboundOrder u OutboundOrder, trazable a un usuario.
- Cada SKU pertenece a un unico cliente.
- Los eventos de inventario no incluyen datos del transportista ni del destinatario final.

### Campos minimos obligatorios para eventos de inventario
- warehouse (los_angeles o zaragoza)
- client_id
- product_id
- product_category
- quantity

## 3) Event Envelope estandar (comun a todos los eventos)

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| eventId | string (UUID v4) | si | Identificador unico por evento |
| timestamp | string (ISO 8601 UTC) | si | Fecha-hora de captura en formato ISO 8601 |
| sessionId | string | si | Identificador de sesion de usuario o sesion tecnica |
| userId | string o null | si | Identificador de usuario autenticado; null si no hay identidad confirmada |
| event_type | string | si | Taxonomia entidad_accion |
| schemaVersion | string | si | Version explicita del esquema, inicial: 1.0.0 |
| requestId | string | si | Correlacion frontend-backend-logs |
| properties | object | si | Solo datos especificos del evento, sin propiedades arbitrarias |

## 4) Catalogo de eventos

Todos los eventos cumplen la frase de diseno:
Capturamos este evento porque necesitamos validar una hipotesis operativa, lo que permite tomar una decision concreta de negocio o tecnica.

| event_type | Clasificacion | Categoria | Hipotesis (porque medir) | Decision habilitada | Stream/Batch y justificacion | Control de frecuencia | Allowlist de properties | PII/sensibilidad y sanitizacion |
|---|---|---|---|---|---|---|---|---|
| inbound_order_created | obligatorio | inventario | Necesitamos saber cuanto volumen entra, por cliente y por almacen. | Planificar capacidad de almacen y personal segun volumen entrante. | stream: evento critico de operacion de almacen. | none | warehouse, client_id, product_id, product_category, quantity, order_id, reference, user_uuid | user_uuid es dato interno pseudonimo; reference se sanitiza (sin texto libre sensible). |
| outbound_order_created | obligatorio | inventario | Necesitamos saber cuantos pedidos se procesan, por cliente y almacen, y a que ritmo. | Detectar cuellos de botella antes de afectar SLA de entrega. | stream: impacta ritmo operativo y SLA. | none | warehouse, client_id, product_id, product_category, quantity, order_id, exit_type, tracking_number_present, user_uuid | user_uuid pseudonimo; no se captura tracking_number completo, solo bandera booleana de presencia. |
| stock_threshold_triggered | obligatorio | inventario | Necesitamos saber frecuencia de quiebre potencial por SKU y cliente. | Alertar a cliente y equipo comercial antes del quiebre. | stream: requiere reaccion operativa inmediata. | dedupe_5m_por_producto_almacen | warehouse, client_id, product_id, product_category, quantity, minimum_threshold, deficit_units | sin PII; solo datos operativos. |
| direct_stock_edit_rejected | obligatorio | inventario | Necesitamos saber intentos de salto de trazabilidad. | Reforzar capacitacion o permisos donde mas ocurre. | stream: evento de cumplimiento operativo. | dedupe_1m_por_usuario_y_producto | warehouse, client_id, product_id, product_category, quantity, attempted_action, rejection_reason, user_uuid | user_uuid pseudonimo; sin captura de payload completo del intento. |
| inventory_discrepancy_detected | obligatorio | inventario | Necesitamos saber en que SKU/almacen hay mas discrepancias. | Priorizar auditorias de inventario en SKU con mayor tasa de discrepancia. | stream: evento clave de control y auditoria. | none | warehouse, client_id, product_id, product_category, quantity, physical_count, system_count, discrepancy_units, audit_id | sin PII; audit_id tecnico. |
| outbound_order_rejected_insufficient_stock | oportunidad identificada | inventario | Necesitamos medir friccion por falta de stock en salida. | Ajustar reglas de reposicion y priorizacion de picking por almacen/cliente. | stream: evita intentos repetidos y retrasos operativos. | dedupe_2m_por_producto_almacen | warehouse, client_id, product_id, product_category, quantity, available_stock, requested_quantity, user_uuid, rejection_reason | user_uuid pseudonimo; sin datos de consumidor final. |
| inventory_order_rejected_warehouse_mismatch | oportunidad identificada | inventario | Necesitamos detectar errores de operacion entre SKU y almacen asignado. | Corregir capacitacion y controles de UI para reducir errores de captura. | stream: error de validacion operativa que bloquea flujo. | dedupe_2m_por_producto_usuario | warehouse, client_id, product_id, product_category, quantity, expected_warehouse, provided_warehouse, order_type, user_uuid | user_uuid pseudonimo; sin PII de cliente final. |
| inventory_form_validation_failed | oportunidad identificada | inventario | Necesitamos saber por que falla la captura en formularios de entrada/salida. | Mejorar UX, validaciones y texto de error para subir tasa de exito. | batch: analisis UX no requiere reaccion en segundos. | aggregate_15m_por_error_code | form_name, error_code, field_name, warehouse, client_id, product_id, product_category, quantity | sin PII; field_name restringido a allowlist controlada. |
| auth_login_succeeded | oportunidad identificada | autenticacion | Necesitamos medir inicio de sesion exitoso por rol y canal para disponibilidad operativa. | Ajustar capacidad de soporte y monitoreo de acceso. | stream: relevante para operacion diaria y seguridad basica. | none | auth_method, user_role, identity_provider, session_age_seconds, device_type | sin email; userId del envelope es suficiente y pseudonimo. |
| auth_login_failed | oportunidad identificada | autenticacion | Necesitamos detectar fallos de acceso y su causa principal. | Activar acciones de soporte, bloqueo progresivo o mejoras de UX de acceso. | stream: prevencion de abuso y continuidad operativa. | dedupe_1m_por_hash_identidad | auth_method, failure_reason, failure_code, identity_hash, device_type | identity_hash irreversible (sha256+salt rotativo); no se guarda email plano. |
| session_access_denied | oportunidad identificada | sesiones | Necesitamos saber cuando usuarios son redirigidos por sesion invalida/ausente. | Detectar expiraciones prematuras o problemas de sesion para corregir configuracion. | stream: afecta acceso a backoffice en tiempo real. | dedupe_1m_por_ruta_y_usuario | route_path, denial_reason, http_status, had_session_cookie | route_path sanitizada (sin query sensible); no se captura cookie. |
| backoffice_navigation_clicked | oportunidad identificada | navegacion | Necesitamos entender uso real de modulos protegidos en backoffice. | Priorizar mejoras en modulos mas usados y simplificar rutas poco usadas. | batch: alto volumen, analitica de producto. | debounce_5s + sampling_50pct + aggregate_15m | from_path, to_path, nav_surface, is_mobile | rutas normalizadas sin parametros sensibles. |
| api_request_latency_sampled | oportunidad identificada | rendimiento_api | Necesitamos visibilidad de latencia por endpoint para detectar degradacion. | Priorizar optimizacion de endpoints y capacidad de infraestructura. | batch: frecuencia alta, valor en tendencia agregada. | sampling_20pct + aggregate_5m_p95 | api_route, method, status_code, latency_ms, upstream_service, request_source | request_source tecnico; no body, no headers sensibles. |
| api_request_failed | oportunidad identificada | errores | Necesitamos detectar fallos de peticiones al gateway/API y su impacto funcional. | Escalar incidentes y priorizar correcciones por severidad y modulo. | stream: errores deben alertar rapido. | dedupe_30s_por_route_status_error | api_route, method, status_code, error_family, error_message_sanitized, retryable, request_source | error_message sanitizado sin stack sensible ni tokens. |
| inventory_form_abandoned | oportunidad identificada | abandono | Necesitamos medir abandono de formularios de inventario antes de enviar. | Reducir friccion de captura en stock entry/exit y subir conversion operativa. | batch: evento de comportamiento, no critico en tiempo real. | debounce_10s + aggregate_30m | form_name, step, dwell_time_seconds, had_validation_error, warehouse, client_id, product_id | sin PII; client_id y product_id son identificadores de negocio no personales. |

## 5) Eventos considerados y descartados

| Evento descartado | Motivo de descarte | Alternativa aplicada |
|---|---|---|
| password_plaintext_submitted | Riesgo critico de privacidad y seguridad. | Solo auth_login_failed con identity_hash irreversible. |
| auth_token_logged | Exposicion de secreto de sesion. | session_access_denied con banderas tecnicas no sensibles. |
| outbound_tracking_number_full_captured | Puede derivar en datos de envio fuera de alcance de inventario. | outbound_order_created con tracking_number_present booleano. |
| raw_request_payload_stored | Alto ruido, coste y riesgo de PII accidental. | allowlists cerradas por evento + error_message_sanitized. |
| consumer_address_captured | Fuera de alcance del sistema de inventario segun contexto. | Exclusion explicita; solo datos de almacen/SKU/cliente B2B. |

## 6) Reglas globales de privacidad y cumplimiento
- Prohibido capturar: contrasenas, tokens, secretos, cookies de autenticacion, headers de autorizacion, payloads completos, direccion o identidad de destinatario final.
- Identificadores potencialmente sensibles deben ir pseudonimizados (identity_hash) o como IDs tecnicos internos (user_uuid).
- Mensajes de error pasan por sanitizacion para remover patrones de secretos, emails y trazas internas.
- event_type y allowlist son cerrados: sin propiedades dinamicas fuera de catalogo.

## 7) Trazabilidad a decisiones
- Inventario: capacidad, SLA operativo, auditoria y cumplimiento.
- Autenticacion/sesion: continuidad operativa del backoffice y soporte de acceso.
- Navegacion/abandono: priorizacion de mejoras UX para reducir friccion.
- Rendimiento/errores API: deteccion temprana de degradacion y respuesta tecnica.

## 8) Sincronizacion con esquemas JSON
- Este documento y [docs/telemetry/event-schemas.json](docs/telemetry/event-schemas.json) comparten exactamente:
  - mismo catalogo de event_type
  - misma allowlist de properties
  - mismos tipos y obligatoriedad
  - misma clasificacion de sensibilidad/PII
  - misma estrategia stream/batch y control de frecuencia
