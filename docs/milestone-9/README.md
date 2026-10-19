# Hito 9 — Flujo Agéntico de RFPs: Recepción y Enrutamiento (Parte 1 de 3)

**Estado:** 32 / 32 tareas completadas ✅  
**Rama:** `feature/rfp-intake`  
**Briefing oficial:** [`trackflow-BRIEFING.es.md`](./trackflow-BRIEFING.es.md)

---

## 🌱 Cómo Empezar el Proyecto (Checklist)

- [x] Crea una rama nueva a partir de tu rama principal: `feature/rfp-intake`.
- [x] Instala las dependencias nuevas que necesites con `uv add` (`uv add "markitdown[pdf]" py-readability-metrics`) — nunca con `pip install` ni `pipenv`.
- [x] Extiende `uis/backoffice` para la UI de subida — no crees una app frontend nueva.
- [x] Añade rutas HTTP en el **backend existente** bajo `services/` (mismo proceso / mismo API). Implementa el pipeline de agentes en `data/pipelines/rfp_intake/`. Pon runners CLI sueltos en `scripts/`.
- [x] Lee tu `trackflow-BRIEFING.es.md` antes de definir departamentos, esquema o RFPs de prueba. Usa los PDF de muestra en `rfp-requests/trackflow/` — súbelos por la UI para verificar el flujo.

---

## 💻 Lo Que Debes Hacer (Checklist)

### Layout del monorepo (no negociable)
- [x] **Sin API nuevo** — extiende el backend existente en `services/`; los routers llaman a `data/pipelines/`
- [x] Implementa el grafo/pipeline de recepción RFP bajo `data/pipelines/` (`rfp_intake` dedicado, no mezclado con el grafo CX)
- [x] Scripts standalone (reproceso manual, smoke runs) viven en `scripts/`, no como segundo HTTP API
- [x] Persiste **Ticket**, **metadatos RFP** y **DepartmentSection.key_aspects** en **PostgreSQL (Supabase)** vía SQLModel (o tu capa DB existente) — TinyDB no es aceptable para estos datos

### Interfaz de recepción (modo ticket)
- [x] Implementa en `uis/backoffice` una interfaz donde se puedan subir RFPs en PDF y se cree un ticket por cada una
- [x] Al subir, guarda el PDF bajo `data/raw/` (artefacto runtime del proceso) y deja el ticket en `analizando`
- [x] El endpoint de subida responde rápido; el pipeline corre en async; la UI consulta/refresca estado (`analizando` → `analisis_completo` o `descartado`)

### Ingesta y conversión del documento
- [x] Convierte cada RFP de PDF a Markdown **antes** de que cualquier agente la lea (obligatorio: MarkItDown o equivalente documentado)
- [x] Extrae metadatos del documento convertido (campos que pide tu BRIEFING)
- [x] Calcula métricas de legibilidad que anticipen el costo de procesamiento (`py-readability-metrics`)
- [x] Guarda metadatos y métricas en PostgreSQL junto al ticket

### Agente clasificador
- [x] Implementa un primer agente que lea el Markdown convertido y determine si es una RFP válida
- [x] Si no lo es, detén el flujo y deja el ticket en `descartado` (no falles en silencio)

### Orquestación por departamento
- [x] Implementa orchestrator-worker-synthesizer: el orquestador descompone en subtareas por departamento
- [x] Cada worker recibe **metadatos + extractos relevantes a su departamento** (sin inventar volúmenes/cifras que no estén en la RFP); guarda `key_aspects` por departamento en PostgreSQL
- [x] El synthesizer consolida un resumen para Ventas (qué pedir a quién)
- [x] En éxito, deja el ticket en `analisis_completo` con handoff claro hacia la Parte 2

### Enrutamiento
- [x] Implementa el enrutamiento del documento clasificado hacia el resto del flujo agéntico (campo `handoff_payload` en DB + contrato de handoff documentado — sin segundo API). El handoff lleva `ticket_id` + payload del synthesizer (`key_aspects` / estructura de workstreams) para que la Parte 2 arranque sin re-parsear el PDF.

### Pruebas
- [x] Incluye pruebas unitarias en `tests/pipelines/` para el agente clasificador y para al menos un agente worker
- [x] Verifica contra los PDF de muestra del BRIEFING (`trackflow-request-1.pdf` formal aceptar, `trackflow-request-2.pdf` informal aceptar, `trackflow-request-3.pdf` inválido rechazar)

---

## ✅ Lo Que Evaluaremos (Checklist)

- [x] Solo el mismo backend API; código de pipeline bajo `data/pipelines/`; sin segundo servicio HTTP
- [x] Ticket, metadatos RFP y aspectos clave persistidos en PostgreSQL (Supabase)
- [x] Los PDF subidos caen en `data/raw/` como parte de la recepción; la UI dispara la subida
- [x] El estado del ticket refleja la realidad: `analizando` → `analisis_completo` o `descartado` (Parte 1); no `esperando_aprobación`
- [x] La subida es async (respuesta rápida + pipeline en background + estado consultable)
- [x] El clasificador rechaza no-RFPs sin detener otros tickets
- [x] Metadatos y métricas de legibilidad almacenados por documento procesado
- [x] Orchestrator-worker-synthesizer como agentes separados en un grafo `rfp_intake` dedicado
- [x] El handoff de enrutamiento lleva `ticket_id` + payload synthesizer / `key_aspects` para la Parte 2
- [x] El resultado final lista aspectos clave + contactos por departamento — verificable contra los PDF de muestra del BRIEFING
- [x] Pruebas unitarias del clasificador y al menos un worker
- [x] La implementación usa los departamentos y el formato de RFP del `trackflow-BRIEFING.es.md` de tu empresa

---

## 🧭 Respuestas a las Preguntas de Diseño

1. **¿Qué pasa si una RFP menciona un departamento que no existe en tu `company-BRIEFING.es.md`? ¿Cómo lo maneja tu clasificador/orquestador?**
   - El orquestador (`decompose_rfp_by_department` en `data/pipelines/rfp_intake/nodes.py`) restringe estrictamente los `departments_needed` al catálogo canónico oficial de TrackFlow (`warehouse`, `lastmile`, `reverse`). Nunca instancia ni despacha un worker para un departamento inexistente. Además, `_detect_unsupported_departments()` en `ingestion.py` registra cualquier área fuera de catálogo mencionada (p. ej., `customs_brokerage`, `marketing`, `manufacturing`) en `metadata.unsupported_departments`, y el Synthesizer las reporta explícitamente en el resumen ejecutivo como *solicitudes fuera de catálogo ignoradas por el orquestador*.

2. **¿Qué necesita realmente cada worker del estado compartido? ¿Le pasas el documento completo o solo lo relevante — y qué haces si falta una cifra requerida?**
   - Cada worker recibe únicamente `DepartmentWorkerInput`: `ticket_id`, `department_id`, `shared_metadata` (nombre y país del cliente, moneda, volumen mensual, fecha límite, presupuesto) y el `relevant_excerpt` segmentado por `_extract_department_slice()` (excluyendo bloques de otros departamentos para evitar contaminación cruzada y alucinaciones). Si falta una cifra requerida (`monthly_volume`, `pallets_requested`, `skus_count`, `avg_parcel_weight` o `return_rate_pct`), el worker deja el campo numérico en `null` (`None`) y registra una pregunta explícita en `open_questions` para que Ventas la valide con el cliente — **jamás inventa cifras**.

3. **¿Cómo decides que un documento "no es una RFP"? ¿Qué pasa con un falso negativo?**
   - El agente clasificador (`classify_rfp_document`) evalúa: (a) longitud mínima e integridad del Markdown extraído, (b) ausencia de patrones de *pitch* entrante de proveedores/transportistas que intentan vender servicios de flota a TrackFlow (`carrier_pitch`), y (c) presencia de intención de contratación de al menos un servicio logístico de TrackFlow (`warehousing`, `last_mile`, `reverse_logistics`). Ante un rechazo, el ticket queda persistido en PostgreSQL con `status = "descartado"`, `rejection_reason` detallado y el objeto `classification`. Si ocurriera un falso negativo, el PDF original permanece en `data/raw/<ticket_id>.pdf` y puede auditarse desde la UI o re-procesarse mediante `scripts/rfp_smoke_test.py --pdf data/raw/<ticket_id>.pdf --ticket-id <ticket_id>`.

4. **¿Qué pasa si dos workers devuelven información contradictoria sobre la misma sección?**
   - Los workers escriben de forma aislada en su propia clave departamental mediante el reducer `merge_worker_outputs`. Al consolidar en el `synthesizer_node`, la función `_detect_cross_worker_conflicts()` ejecuta validaciones cruzadas deterministas preparando los triggers de arbitraje fijo definidos en §7 del BRIEFING (`volume-vs-capacity`, `returns-sla-breach`, `currency-mismatch`) y los adjunta en `handoff_payload.potential_conflicts` señalando al árbitro responsable (Miguel Torres o Sofía Ramos) sin que los agentes negocien por consenso libre.

5. **¿Dónde corre el trabajo async (background task, worker process, Prefect) — y cómo el ticket sigue siendo verdad si el job falla a mitad de pipeline?**
   - El endpoint `POST /api/rfp/upload` persiste el archivo en `data/raw/<ticket_id>.pdf`, crea la fila `RFPTicket` en PostgreSQL con `status = "analizando"`, encola `_execute_rfp_pipeline_background` mediante `BackgroundTasks` de FastAPI y responde inmediatamente `HTTP 202 Accepted`. Tanto `run_rfp_intake_pipeline` (`graph.py`) como `_execute_rfp_pipeline_background` (`routes/rfp.py`) cuentan con bloques `try/except` anti-zombie que, ante cualquier excepción a mitad del grafo, actualizan inmediatamente el ticket en PostgreSQL a `status = "descartado"` registrando el detalle del fallo en `rejection_reason`, garantizando que ningún ticket quede bloqueado indefinidamente en `analizando`.

---

## 📦 Ejemplo de Ejecución para Descripción del Pull Request

Al procesar **`rfp-requests/trackflow/trackflow-request-1.pdf`** (_ModaViva_, España, RFP formal con almacenamiento + devoluciones y transportista propio de última milla):

```json
{
  "file": "trackflow-request-1.pdf",
  "status": "analisis_completo",
  "client_name": "ModaViva",
  "client_country": "Spain",
  "currency": "EUR",
  "departments_needed": ["warehouse", "reverse"],
  "excluded_departments": ["lastmile"],
  "readability_metrics": {
    "flesch_kincaid_grade": 17.6,
    "gunning_fog": 21.14,
    "word_count": 267
  },
  "what_to_ask_each_department": {
    "warehouse": {
      "contact_person": "Ana Whitfield",
      "deliverable_requested": "Capacidad de almacenamiento, costo por pallet/SKU, tiempo de onboarding"
    },
    "reverse": {
      "contact_person": "Sofía Ramos",
      "deliverable_requested": "Costo y tiempo de procesamiento de devoluciones (si el cliente lo solicita)"
    }
  },
  "ready_for_part_2": true
}
```
