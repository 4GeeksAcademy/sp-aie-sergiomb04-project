# Hito 9 — Flujo Agéntico de RFPs: Generación de Respuestas (Parte 2 de 3)

**Estado:** 23 / 23 tareas completadas ✅  
**Rama:** `feature/rfp-response-generation`  
**Briefing oficial:** [`trackflow-BRIEFING.es.md`](./trackflow-BRIEFING.es.md)

---

## 🎯 Resumen Ejecutivo del Hito

En la Parte 1 establecimos el pipeline de recepción, triage con clasificador, extracción documental y segmentación hacia los departamentos activos (`warehouse`, `lastmile`, `reverse`).

En esta **Parte 2**, el sistema automatiza la redacción y evaluación rigurosa de la propuesta económica:
1. **Consumo del handoff de la Parte 1:** Inicia exclusivamente desde el contrato persistido en PostgreSQL (`ticket_id` + metadatos + `key_aspects`), sin re-parsear el PDF crudo.
2. **Generadores por departamento:** Agentes especializados para `warehouse` (Ana Whitfield), `lastmile` (Carlos Vega) y `reverse` (Sofía Ramos) que cotizan tarifas, plazos de onboarding, SLAs y escalados según el país (`client_country`: USD para EE. UU., EUR para España).
3. **Evaluación concurrente en paralelo:** Tres agentes independientes evalúan cada borrador:
   - **Legibilidad:** Calculada con `py-readability-metrics` y validación de extensión/estructura.
   - **Pertinencia:** Cobertura de requerimientos del cliente y aspectos clave departamentales.
   - **Cumplimiento (§5):** Validación estricta de las 5 reglas de negocio de TrackFlow (moneda, SLA de entrega %, prohibición de procesamiento de devoluciones < 48h, tabla de descuentos por volumen y no divulgación de tarifas internas negociadas).
4. **Ciclo Generador-Evaluador y Límite de Iteraciones:** Si un borrador no pasa, se reinyecta feedback concreto y accionable al generador correspondiente. Si se agota el límite (`max_iterations = 3`), el último borrador y su `EvaluationResult` se conservan como provisionales y el ticket pasa a `needs_human_review` sin ser descartado.

---

## 💻 Lo Que Debes Hacer (Checklist 14 / 14)

### Consumir el enrutamiento de la Parte 1
- [x] La entrada de la Parte 2 lee el handoff de enrutamiento de la Parte 1 (`ticket_id` + payload del synthesizer / `key_aspects`, vía el flag de cola, campo DB o contrato documentado de la Parte 1) — los generadores no deben re-ingerir el PDF crudo como input principal

### Generación por departamento
- [x] Implementa un agente generador por departamento que reciba el resumen relevante producido en la Parte 1 (desde ese handoff)
- [x] El agente generador debe producir contenido específico para la sección de propuesta económica de su departamento

### Evaluación en paralelo
- [x] Implementa múltiples agentes evaluadores que corran en paralelo sobre cada sección generada
- [x] Al menos un evaluador debe revisar legibilidad (se sugiere `py-readability-metrics`)
- [x] Al menos un evaluador debe revisar pertinencia (que el contenido responda lo que pide la RFP)
- [x] Al menos un evaluador debe revisar cumplimiento de los lineamientos definidos en tu `company-BRIEFING.md`
- [x] Persiste la evaluación de cada sección como un `EvaluationResult` estructurado (`section_id / department_id`, `readability`, `relevance`, `compliance`, `overall_pass`, `feedback_for_generator`)

### Ciclo generador-evaluador
- [x] Si una sección falla la evaluación, el flujo debe devolverla al agente generador correspondiente junto con el `feedback_for_generator` del `EvaluationResult`
- [x] Define y aplica un límite de iteraciones para evitar que el ciclo generador-evaluador se repita indefinidamente (`max_iterations = 3`)
- [x] Cuando se agota el límite sin pasar: conserva el último borrador + su `EvaluationResult`, marca la sección (y el ticket si aplica) como `needs_human_review`, e inclúyela igual en el handoff a la Parte 3 — no descartes el ticket

### Estado del ticket
- [x] Actualiza el ticket creado en la Parte 1 (desde `analisis_completo`) para reflejar el progreso de la generación y evaluación (`generando_borrador`, `en_evaluación`, `needs_human_review`). Persiste borradores y `evaluation_results` en PostgreSQL. Sigue sin crear un API nuevo: extiende el backend existente y el pipeline bajo `data/pipelines/`.

### Pruebas
- [x] Incluye pruebas unitarias en `tests/pipelines/` para al menos un agente generador y un agente evaluador, incluyendo un caso donde la evaluación falla
- [x] Añade un caso de fallo de compliance anclado a una regla de tu `company-BRIEFING.md` (p. ej. un borrador que promete algo que los lineamientos prohíben → `compliance.pass == false`)

---

## ✅ Lo Que Evaluaremos (Checklist 9 / 9)

- [x] Cada departamento tiene su propio agente generador, claramente separado de los demás
- [x] La Parte 2 consume el handoff de enrutamiento de la Parte 1 (`ticket_id` + payload synthesizer / `key_aspects`) — no re-parsea el PDF como input principal del generador
- [x] Los evaluadores corren en paralelo y no bloquean la ejecución de otros departamentos entre sí
- [x] El sistema aplica correctamente el ciclo generador-evaluador, incluyendo el límite de iteraciones y el handoff `needs_human_review` al agotarlo
- [x] El ticket refleja con precisión el progreso de generación y evaluación en tiempo real
- [x] La salida de evaluación sigue la forma `EvaluationResult` (legibilidad / pertinencia / compliance estructurados — no texto libre sin estructura)
- [x] Los borradores y `evaluation_results` se persisten en PostgreSQL; sigue habiendo un solo API backend bajo `services/` (sin un segundo servicio HTTP)
- [x] Existen pruebas unitarias que cubren éxito, un fallo genérico de evaluación, y un fallo de compliance anclado al BRIEFING
- [x] La implementación usa los lineamientos y formatos definidos en el `company-BRIEFING.md` de tu empresa

---

## 🧭 Respuestas a las Preguntas de Diseño

### 1. ¿Qué información del estado necesita realmente cada agente evaluador? ¿Le estás pasando solo la sección que debe revisar o el documento completo?
Cada agente evaluador recibe únicamente el contexto mínimo indispensable para su función, evitando inyecciones de texto masivas y previniendo alucinaciones o confusiones de alcance:
- `evaluate_readability` recibe **únicamente el texto del borrador** (`draft`) de la sección generada y extrae métricas estadísticas y de legibilidad objetivas con `py-readability-metrics`.
- `evaluate_relevance` recibe el **borrador de la sección**, el **`department_id`** y el diccionario de **`key_aspects`** producido para ese departamento específico en la Parte 1 (sus `scope_items` y `what_to_contribute`), verificando si se respondieron las necesidades puntuales sin requerir el resto de la propuesta.
- `evaluate_compliance` recibe el **borrador de la sección**, el **`department_id`** y el **`client_country`** del cliente (para verificar moneda oficial USD vs. EUR), evaluando exclusivamente contra las 5 reglas de negocio de TrackFlow (§5).

### 2. ¿Cómo evitas que dos evaluadores en paralelo entren en conflicto al escribir su resultado en el estado compartido?
Los evaluadores de legibilidad, pertinencia y cumplimiento se ejecutan de forma concurrente e independiente mediante tareas aisladas (`asyncio.gather` con `asyncio.to_thread`). Cada evaluador es una función pura que no muta el estado global ni escribe directamente en la base de datos; retorna su propio sub-objeto estructurado (`ReadabilityEvaluation`, `RelevanceEvaluation`, `ComplianceEvaluation`). El orquestador consolida los tres resultados de forma determinista en un único objeto inmutable `EvaluationResult` antes de persistir la transacción en la fila `DepartmentSection` correspondiente en PostgreSQL, eliminando cualquier condición de carrera.

### 3. Cuando una sección llega a `needs_human_review` tras agotar iteraciones, ¿cómo se lo muestras a Ventas para que sepa qué borrador es provisional?
En la interfaz de Backoffice (`uis/backoffice/app/(protected)/rfp/page.tsx`):
1. **Banner superior de advertencia:** Se activa un banner de alerta ámbar destacado (`rfp-needs-human-review-banner`) indicando explícitamente que el ticket requiere intervención humana porque una o más secciones agotaron el límite de reintentos automatizados.
2. **Badge visual:** El estado del ticket y de la sección específica se marca con la insignia `⚠️ Requiere Revisión Humana (Borrador provisional)`.
3. **Anotación de borrador provisional:** En la tarjeta de la sección afectada se muestra la leyenda `(Borrador provisional conservado tras agotar iteraciones)` junto con el desglose exacto de las infracciones y el feedback detallado que motivó la pausa, permitiendo al equipo comercial de Miguel Torres identificar en segundos qué ajustar antes de la aprobación en la Parte 3.

### 4. ¿El feedback que recibe el generador tras un fallo es lo suficientemente específico como para corregir el problema real, o es genérico?
El feedback es altamente específico, categorizado y accionable. En lugar de indicar `"error de validación"`, desglosa la causa raíz:
- **Cumplimiento de moneda:** `[Cumplimiento de Lineamientos §5]: Corregir las siguientes infracciones: currency_match: El cliente opera en España; la cotización debe ser en EUR (€), no en USD ($).`
- **Cumplimiento de SLA de devoluciones:** `[Cumplimiento de Lineamientos §5]: Corregir las siguientes infracciones: no_returns_under_48h: Ninguna propuesta puede prometer procesamiento de devoluciones en menos de 48 horas (viola §5).`
- **Tabla de descuentos:** `[Cumplimiento de Lineamientos §5]: Corregir las siguientes infracciones: volume_discount_table: Toda propuesta debe incluir una tabla formal de descuentos por volumen.`
- **Pertinencia:** `[Pertinencia]: Falta abordar los siguientes aspectos clave: Falta especificar el tiempo o proceso de onboarding.`
Esto permite que el generador corrija de inmediato la deficiencia concreta en la siguiente iteración.

---

## 📦 Ejemplos de Evaluación para Descripción del Pull Request

### Ejemplo 1: Sección que Pasa la Evaluación (Aprobado ✅)
**Departamento:** `warehouse` (Ana Whitfield) — Cliente: *ModaViva* (España, EUR)

```markdown
### Propuesta Económica y Técnica: Warehouse Operations
**Responsable del Departamento:** Ana Whitfield  
**Cliente:** ModaViva (Spain)  
**Moneda Oficial de Cotización:** EUR (€)

#### 1. Capacidad de Almacenamiento y Operaciones de Almacén
TrackFlow pone a disposición de ModaViva su moderna infraestructura logística con capacidad garantizada para gestión de stock, recepción de mercancía y preparación de pedidos. La operativa contempla una capacidad inicial estimada para soportar un volumen mensual de 12,000 unidades...
- **Almacenamiento mensual por pallet:** €14.50 / mes
- **Preparación de pedidos (Pick & Pack):** €2.10

#### 2. Plazos de Onboarding y Coordinación Operativa
El proceso integral de onboarding e integración con el WMS se completará en un plazo garantizado de 10 días hábiles desde la firma del acuerdo.

#### 3. Compromiso de Calidad y SLA Operativo
TrackFlow garantiza un **SLA de entrega a tiempo del 98.5%** en la expedición y preparación de pedidos.

#### 4. Tabla de Descuentos por Volumen (Almacenamiento y Manipulación)
| Rango de Volumen Mensual (Unidades) | Descuento en Almacenamiento | Descuento en Picking | Tarifa Efectiva Pick&Pack (EUR) |
| :--- | :--- | :--- | :--- |
| 1 - 2.500 unidades | Tarifa base (0%) | 0% | €2.10 |
| > 10.000 unidades | 15% de descuento | 12% | €1.85 |
```

**Resultado de Evaluación (`EvaluationResult`):**
```json
{
  "department_id": "warehouse",
  "readability": { "pass": true, "score": 48.72, "details": { "summary": "Legibilidad adecuada para propuesta formal" } },
  "relevance": { "pass": true, "missing_aspects": [] },
  "compliance": { "pass": true, "rule_ids": ["currency_match", "delivery_sla_percentage", "no_returns_under_48h", "volume_discount_table", "no_carrier_negotiated_rates"], "violations": [] },
  "overall_pass": true,
  "feedback_for_generator": "La sección cumple con todos los lineamientos de legibilidad, pertinencia y cumplimiento."
}
```

---

### Ejemplo 2: Sección que Falla Evaluación (Infracción de Reglas §5 ❌)
**Departamento:** `reverse` (Sofía Ramos) — Intento con turnaround en 24h y cotización en USD para España

```markdown
### Propuesta Reverse Logistics
Sofía Ramos ofrece procesamiento exprés de devoluciones para ModaViva.
Garantizamos la inspección completa y turnaround de devoluciones en 24 horas desde la recepción.
Coste por unidad: $4.50 USD.
SLA de entrega a tiempo del 99%.
```

**Resultado de Evaluación (`EvaluationResult`):**
```json
{
  "department_id": "reverse",
  "readability": { "pass": false, "score": 38.1, "details": { "violations": ["Longitud insuficiente (42 palabras; mínimo requerido: 50)."] } },
  "relevance": { "pass": true, "missing_aspects": [] },
  "compliance": {
    "pass": false,
    "rule_ids": ["currency_match", "delivery_sla_percentage", "no_returns_under_48h", "volume_discount_table", "no_carrier_negotiated_rates"],
    "violations": [
      "currency_match: El cliente opera en España; la cotización debe ser en EUR (€), no en USD ($).",
      "no_returns_under_48h: Ninguna propuesta puede prometer procesamiento de devoluciones en menos de 48 horas (viola §5).",
      "volume_discount_table: Toda propuesta debe incluir una tabla formal de descuentos por volumen."
    ]
  },
  "overall_pass": false,
  "feedback_for_generator": "[Legibilidad]: Longitud insuficiente (42 palabras; mínimo requerido: 50).\n[Cumplimiento de Lineamientos §5]: Corregir las siguientes infracciones: currency_match: El cliente opera en España; la cotización debe ser en EUR (€), no en USD ($).; no_returns_under_48h: Ninguna propuesta puede prometer procesamiento de devoluciones en menos de 48 horas (viola §5).; volume_discount_table: Toda propuesta debe incluir una tabla formal de descuentos por volumen."
}
```
