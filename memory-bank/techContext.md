# Technical Context - TrackFlow

## Stack tecnologico actual
### Entorno de proyecto (repositorio)
- Monorepo estructurado por dominios: apps, packages, data, docs, agents, skills, workflows.
- Frontend clasico inicial en raiz: HTML + JavaScript + Tailwind via CDN.
- App moderna en desarrollo: Next.js (App Router) + React + TypeScript + TailwindCSS + ESLint en apps/talent-pipeline-tracker.
- Paquete compartido de tipos: packages/shared (@repo/shared-types).

### Contexto tecnologico de negocio (empresa)
- Dos sistemas de gestion de almacen distintos (uno comercial, otro basado en hoja de calculo).
- ERP legado (arquitectura antigua).
- Scripts punto a punto en Python con documentacion incompleta.
- Datos y servicios distribuidos en dos proveedores cloud.

## Problemas tecnicos identificados
- Arquitectura heterogenea y acoplada por integraciones ad hoc.
- Falta de observabilidad centralizada (logs, metricas, alertas).
- Ausencia de modelo de datos unificado entre paises y areas.
- Trazabilidad limitada de incidencias (dependencia de canales manuales como mensajeria).
- Procesos criticos manuales: tracking multicarrier, devoluciones, reporting ejecutivo.
- Time-to-delivery tecnico alto para nuevas funcionalidades.

## Arquitectura del monorepo
- apps/: aplicaciones de producto (portales, dashboards, frontends por dominio).
- packages/shared/: tipos y contratos compartidos para reducir duplicidad.
- data/: base para pipelines, datasets y analitica.
- skills/ y agents/: patrones y recursos para agentes de IA.
- docs/, workflows/, scripts/: documentacion operativa y automatizaciones.
- memory-bank/: contexto persistente del proyecto para agentes.

## Restricciones tecnicas del proyecto
- Operacion multinacional: dos paises, dos entornos operativos y distintos sistemas origen.
- Disponibilidad elevada: flujos clave deben funcionar 24/7.
- Integracion con multiples transportistas y APIs externas heterogeneas.
- Necesidad de explicabilidad en decisiones automatizadas (por ejemplo, seleccion de carrier).
- Dependencia de sistemas legados que no pueden reemplazarse de golpe.
- Riesgo de deuda tecnica por coexistencia de stack nuevo y componentes legacy.

## Posibles servicios, APIs y dashboards futuros
### Servicios/APIs
- API de inventario unificada por SKU/almacen.
- Servicio de ingesta y normalizacion de pedidos desde email/documentos.
- Motor de seleccion de transportista con scoring explicable.
- API de tracking unificado multicarrier.
- Servicio de reglas para aprobacion automatica de devoluciones.
- Servicio de notas/tickets y asistente de CX con RAG.
- Servicio de scoring de salud de cliente y riesgo de renovacion.

### Dashboards
- Operaciones de almacen: stock, discrepancias, throughput, alertas.
- Transportistas: on-time rate, incidencias, coste por kg/ruta.
- Devoluciones: volumen, causas, tiempos de resolucion, recuperacion.
- CX: volumen de tickets, tiempo de respuesta, sentimiento.
- Comercial: salud de cuentas, renovaciones, oportunidades.
- Ejecutivo global: KPIs por pais y vista consolidada en tiempo real.

## Direccion recomendada para implementacion
- Priorizar contratos de datos y APIs compartidas antes de escalar UIs.
- Instrumentar observabilidad desde etapas tempranas.
- Evolucionar por capas: integracion de datos -> automatizacion operativa -> agentes IA.
- Definir governance de tipos y eventos para mantener consistencia entre apps.