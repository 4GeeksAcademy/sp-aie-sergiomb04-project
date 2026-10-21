# Hito 9 — Flujos de Trabajo Agénticos: Aprobación y Cierre (Parte 3 de 3)

**Estado:** Completado ✅  
**Rama:** `feature/rfp-approval-completion`  
**Briefing oficial:** [`trackflow-BRIEFING.es.md`](./trackflow-BRIEFING.es.md)

---

## 🎯 Resumen Ejecutivo del Hito

En la **Parte 1** se construyó la recepción, triage y segmentación departamental. En la **Parte 2** se implementaron los generadores de propuestas y el ciclo evaluador en paralelo (legibilidad, pertinencia y cumplimiento §5).

En esta **Parte 3**, el sistema culmina el flujo agéntico corporativo con:
1. **Aprobación Humana Aislada (HITL) con `interrupt()`:**
   - Cada departamento activo entra en una compuerta de interrupción explícita.
   - La pausa afecta **únicamente** a la rama del departamento en espera, permitiendo que los demás avancen concurrentemente.
   - Checkpointer persistente [`SqliteSaver`](file:///d:/workspace/sp-aie-sergiomb04-project/data/pipelines/rfp_intake/approval_flow.py) con namespaces por hilo `rfp-{ticket_id}:{department_id}`.
   - Punto de entrada de reanudación `Command(resume=...)` que valida la decisión humana: `approve` (aprobar), `reject` (rechazar) o `request_changes` (solicitar cambios).
2. **Nodo de Arbitraje Dedicado (§7 BRIEFING):**
   - Resolución determinista basada en estado estructurado ante contradicciones detectables:
     - `volume-vs-capacity` → Árbitro fijo: **Miguel Torres** (Director Comercial). Regla: Limitar el volumen de la propuesta a la capacidad de warehouse; lastmile revisa volumen/costo a la baja.
     - `returns-sla-breach` → Árbitro fijo: **Sofía Ramos** / Miguel Torres. Regla: Forzar `request_changes` en toda sección que prometa devoluciones en < 48h.
     - `currency-mismatch` → Árbitro fijo: **Miguel Torres**. Regla: Reescribir a la moneda oficial del país del cliente (USD para EE. UU., EUR para España).
     - **Prohibición estricta de consenso o votación por LLMs:** árbitros humanos y reglas fijas auditadas.
3. **Trazabilidad Integral y Límite de Iteraciones:**
   - Registro de trazas de auditoría con `agent`, `input`, `output` y `timestamp` (UTC ISO).
   - Límite estricto de iteraciones (`max_iterations = 3`) que impide bucles infinitos en solicitudes de cambios.
4. **Estados del Ciclo de Vida y UI Backoffice:**
   - Estado `esperando_aprobación` mientras haya departamentos pendientes de sign-off.
   - Estado `terminado` una vez que todos los departamentos han aprobado y el documento final ha sido persistido.
5. **Síntesis Automática del Documento Final (`RFPFinalDocument`):**
   - Consolidación automática de todos los extractos aprobados, resumen ejecutivo, tabla de firmas de responsables y notas de arbitraje.

---

## 💻 Lo Que Se Ha Implementado

### 1. Interrupción y Aislamiento (HITL)
- [x] Función `interrupt()` invocada antes de aprobar la sección de cada departamento en `data/pipelines/rfp_intake/approval_flow.py`.
- [x] Aislamiento estricto por rama departamental: pausar `warehouse` no bloquea la revisión ni aprobación de `lastmile` o `reverse`.
- [x] Checkpointer persistente `SqliteSaver` (con base de datos SQLite en `data/checkpoints/rfp_approval.db` y soporte en memoria para tests).
- [x] Namespaces de hilos estructurados como `rfp-{ticket_id}:{department_id}`.
- [x] Reanudación explícita con `Command(resume=decision_payload)` validando decisiones de aprobación, rechazo y solicitud de cambios.

### 2. Arbitraje y Trazabilidad (§7 BRIEFING)
- [x] Nodo de arbitraje explícito (`detect_and_resolve_conflicts` en `data/pipelines/rfp_intake/arbitration.py`).
- [x] Respuestas deterministas para los 3 triggers del BRIEFING: `volume-vs-capacity`, `returns-sla-breach` y `currency-mismatch`.
- [x] Asignación obligatoria de árbitro fijo (Miguel Torres / Sofía Ramos) sin votaciones ni consensos de LLMs.
- [x] Registro estructurado de trazas de auditoría (`TraceStep`) con `agent`, `input`, `output` y `timestamp`.
- [x] Límite estricto de iteraciones (`max_iterations = 3`) protegiendo el ciclo de cambios.

### 3. Estados y Backoffice UI
- [x] Actualización de estados del ticket: `esperando_aprobación` durante la revisión humana y `terminado` tras el cierre.
- [x] Interfaz en `uis/backoffice/app/(protected)/rfp/page.tsx` con paneles interactivos de sign-off por departamento (Aprobar, Solicitar Cambios, Rechazar).
- [x] Panel de verificación de arbitraje en tiempo real con alertas y visualización de resoluciones de conflictos.
- [x] Visor del documento final consolidado con desglose de secciones y firmas de responsables.
- [x] Endpoints API en FastAPI (`services/api/trackflow_api/routes/rfp.py`) y proxies Next.js en `uis/backoffice/app/api/rfp/`.

### 4. Síntesis Final
- [x] Consolidación automática en `RFPFinalDocument` (tabla `rfp_final_documents` en PostgreSQL) cuando todos los departamentos activos completan su sign-off.
- [x] Generación de propuesta integral en formato markdown con resumen ejecutivo, cotizaciones por departamento, tabla formal de firmas y notas de arbitraje.

---

## 🧭 Respuestas a las Preguntas de Diseño

### 1. ¿Cómo se garantiza que pausar un departamento no bloquee a los demás en LangGraph?
LangGraph gestiona el estado a través de checkpointers indexados por `configurable.thread_id`. Al configurar un namespace diferenciado por departamento (`rfp-{ticket_id}:{department_id}`), cada departamento opera en su propio grafo/hilo de ejecución independiente. Cuando el nodo de revisión de Warehouse llama a `interrupt()`, el motor de LangGraph guarda el checkpoint exclusivo de ese `thread_id` y detiene su ejecución sin afectar los hilos de `lastmile` o `reverse`, los cuales pueden seguir recibiendo inspecciones y reanudaciones concurrentes.

### 2. ¿Por qué el arbitraje debe ser un nodo fijo y no un debate entre agentes LLM?
En contratación corporativa y SLAs de e-commerce, los acuerdos no pueden resolverse mediante consenso estocástico o alucinaciones entre agentes. El `trackflow-BRIEFING.es.md` §7 define con precisión qué directivo tiene autoridad final sobre cada discrepancia operativa (Miguel Torres en capacidad comercial y divisas; Sofía Ramos en logística inversa). Un nodo determinista garantiza predictibilidad legal, trazabilidad auditable y apego incondicional a las políticas de TrackFlow.

### 3. ¿Qué ocurre si un responsable solicita cambios en su sección?
Al registrar `action = "request_changes"` con notas técnicas, el sistema incrementa el contador de iteraciones de la sección. Si `iteration <= max_iterations`, se re-dispara el generador departamental correspondiente inyectando las observaciones como feedback para regenerar el borrador y volver a someterlo a evaluación. Si se supera el límite de 3 iteraciones sin acuerdo, la sección se marca para intervención del árbitro comercial (Miguel Torres) sin dejar el ticket bloqueado indefinidamente.

---

## 🧪 Pruebas Automatizadas

Se dispone de una suite completa de 30 pruebas automatizadas pasando al 100%:
- `tests/pipelines/test_rfp_approval.py`:
  - `test_department_approval_graph_pauses_at_interrupt`: Verificación de pausa en compuerta `interrupt()`.
  - `test_department_approval_resumption_with_approve`: Verificación de reanudación con `Command(resume=...)` y persistencia en DB.
  - `test_parallelism_approving_department_b_while_a_remains_interrupted`: Aprobación de Last Mile mientras Warehouse permanece interrumpido.
  - `test_arbitration_trigger_currency_mismatch`: Detección y resolución de trigger de divisa por Miguel Torres.
  - `test_arbitration_trigger_returns_sla_breach`: Detección y forzado de cambios en devoluciones < 48h por Sofía Ramos.
  - `test_arbitration_trigger_volume_vs_capacity`: Limitación de volumen a capacidad de warehouse por Miguel Torres.
  - `test_e2e_full_rfp_lifecycle_intake_to_approval_completion`: Ejecución completa reproducible de punta a punta (Partes 1 a 3).
- `services/api/tests/test_rfp_routes.py`:
  - Endpoints de subida, generación, inicio de aprobación, arbitraje, registro de decisiones y consulta de documento final.
- `tests/pipelines/test_rfp_generation.py`: 12 pruebas de generadores y evaluadores paralelos.
- `tests/pipelines/test_rfp_intake.py`: 8 pruebas de ingesta y triage.
