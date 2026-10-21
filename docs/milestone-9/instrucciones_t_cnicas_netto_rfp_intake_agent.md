# TASK SPEC: RFP Intake & Routing Workflow (Part 1 of 3)

## 1. Contexto & Restricciones Duras (Non-Negotiable)
- **Monorepo:** Trabajar sobre el monorepo existente en branch `feature/rfp-intake`. No inicializar repositorios nuevos.
- **Single Backend:** Prohibido crear nuevos microservicios o servidores HTTP paralelos. Extender los routers existentes en `services/`.
- **Pipeline Isolation:** Grafo dedicado LangGraph (o equivalente) ubicado estrictamente en `data/pipelines/rfp_intake/`. No vincular nodos al grafo CX / knowledge-agent.
- **Scripts:** Tareas standalone, pruebas de humo y re-procesamiento manual deben residir en `scripts/`.
- **Gestor de Dependencias:** Usar exclusivamente `uv add <paquete>`. Prohibido el uso de `pip install` o `pipenv`.
- **Persistencia:** PostgreSQL (Supabase) mediante SQLModel/capa ORM existente. Prohibido usar TinyDB o JSONs como fuente de la verdad.
- **Single Source of Truth:** Consultar `CONTEXT-company.md` para extraer departamentos oficiales, campos de metadatos requeridos y PDFs de prueba (`rfp-requests/<empresa>/`). No inventar departamentos genéricos.

---

## 2. Dependencias Obligatorias
Ejecutar en la raíz del entorno:
```bash
uv add markitdown py-readability-metrics
```

---

## 3. Modelo de Datos y Estados (PostgreSQL / SQLModel)
Asegurar o extender las tablas con los siguientes campos y relaciones:

- **Ticket Lifecycle (Estados permitidos en Parte 1):**
  - `analizando`: Archivo recibido, PDF guardado y pipeline async en ejecución.
  - `descartado`: Clasificador determinó que el documento no es una RFP válida.
  - `analisis_completo`: Pipeline finalizado exitosamente por el synthesizer; listo para Ventas y Parte 2.
  *(Nota: NO usar `esperando_aprobacion` en esta fase).*

- **Entidades mínimas a persistir:**
  1. `Ticket`:
     - `id`: UUID / ID único.
     - `status`: Enum (`analizando`, `descartado`, `analisis_completo`).
     - `pdf_path`: Ruta relativa del archivo en storage local (`data/raw/<ticket_id>.pdf`).
     - `created_at`, `updated_at`: Timestamps.
  2. `RFPMetadata`:
     - `ticket_id`: Foreign key a `Ticket`.
     - `raw_markdown`: Contenido convertido del documento.
     - `metadata`: JSON con los campos de negocio definidos en `CONTEXT-company.md`.
     - `readability_metrics`: JSON con métricas calculadas (Flesch-Kincaid, Gunning Fog, etc.).
  3. `DepartmentSection` (o equivalente de workstreams):
     - `id`: ID único.
     - `ticket_id`: Foreign key a `Ticket`.
     - `department`: Nombre del departamento (estrictamente alineado a `CONTEXT-company.md`).
     - `key_aspects`: JSON / texto estructurado con los puntos clave extraídos por cada worker.
     - `contact_person` / `handoff_payload`: Información procesada por el synthesizer.

---

## 4. Endpoints y Lógica Async en `services/`
Modificar el router existente de tickets/RFPs:

- `POST /api/rfp/upload` (o ruta equivalente de tickets del backend):
  1. Recibe el archivo PDF.
  2. Guarda el binario en disco bajo `data/raw/<ticket_id>.pdf`.
  3. Crea registro `Ticket` en DB con estado `analizando`.
  4. Dispara la ejecución del pipeline agéntico en background (e.g. `BackgroundTasks` de FastAPI o worker async).
  5. Retorna inmediatamente HTTP `202 Accepted` con payload: `{"ticket_id": "<id>", "status": "analizando"}`.

- `GET /api/rfp/{ticket_id}`:
  1. Consulta el estado del ticket y datos asociados en PostgreSQL.
  2. Retorna estado actual (`analizando`, `descartado`, `analisis_completo`), metadatos, métricas y el breakdown por departamento cuando esté listo.

---

## 5. Arquitectura del Pipeline (`data/pipelines/rfp_intake/`)
Diseñar el flujo orquestado (Orchestrator-Worker-Synthesizer) con LangGraph:

1. **Paso 0: Conversión e Ingesta:**
   - Convertir PDF a Markdown usando `MarkItDown`.
   - Extraer métricas de legibilidad (`py-readability-metrics`).
   - Extraer metadatos base solicitados por el contexto.
   - Persistir métricas y metadatos en PostgreSQL.

2. **Nodo 1: Clasificador (Triage Agent):**
   - Evalúa si el texto en Markdown constituye una RFP real de acuerdo a los criterios del `CONTEXT-company.md`.
   - **Branch Condicional:**
     - Si NO es RFP: Actualizar `Ticket.status = "descartado"`, finalizar ejecución (no fallar silenciosamente).
     - Si ES RFP: Continuar al orquestador.

3. **Nodo 2: Orquestador (Decomposition):**
   - Mapea las secciones y requerimientos del documento hacia los departamentos válidos de la empresa.
   - Segmenta y envía a cada worker **únicamente** los metadatos globales y los extractos de texto relevantes a su área (prohibido pasar todo el PDF a cada worker si genera alucinaciones).

4. **Nodos 3..N: Workers por Departamento (Paralelo):**
   - Un worker por cada departamento involucrado.
   - Analiza su sección, extrae alcances, restricciones y recursos requeridos sin alucinar cifras inexistentes.
   - Escribe sus resultados en `DepartmentSection.key_aspects`.

5. **Nodo 4: Sintetizador (Synthesizer Agent):**
   - Recibe la consolidación de todos los workers.
   - Genera el resumen ejecutivo para el equipo de Ventas: "¿Qué pedirle a qué departamento?".
   - Prepara el payload estructurado de handoff (para el consumo de la Parte 2).
   - Actualiza `Ticket.status = "analisis_completo"`.

---

## 6. Frontend: `uis/backoffice`
- Extender la UI actual (sin crear un proyecto frontend nuevo).
- Formulario de subida de PDF con envío al endpoint existente.
- Polling sobre el `ticket_id` para reflejar transiciones: `analizando` $\rightarrow$ `analisis_completo` o `descartado`.
- Vista de resultados: Mostrar métricas de legibilidad, metadatos y desglose de `key_aspects` por departamento para tickets completados.

---

## 7. Pruebas y Validación (Checklist de Aprobación)
Implementar y verificar:

- [x] **Tests Unitarios (`tests/pipelines/`):**
  - Test para el agente clasificador (debe clasificar correctamente muestras válidas y rechazar inválidas).
  - Test unitario para al menos un worker departamental aislado.
- [x] **Smoke Tests de Integración:**
  - Probar con los PDFs de muestra de `rfp-requests/<empresa>/`:
    - RFP formal $\rightarrow$ Estado final `analisis_completo`.
    - RFP informal $\rightarrow$ Estado final `analisis_completo`.
    - Documento inválido $\rightarrow$ Estado final `descartado`.
- [x] **Handoff Contract:** El ticket completado debe contener el payload estructurado (`ticket_id` + output del synthesizer) listo para el hito 2 sin necesidad de re-procesar el PDF.