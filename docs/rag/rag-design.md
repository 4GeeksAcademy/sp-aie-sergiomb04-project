# Documento de Diseño RAG y Base de Conocimiento — TrackFlow

## 1. Visión General y Objetivos de Negocio

El sistema de **Retrieval-Augmented Generation (RAG)** de TrackFlow Tech fue diseñado para dotar al equipo comercial y de soporte (liderado por Miguel Torres, Director Comercial) de una herramienta confiable para responder preguntas frecuentes de prospectos y clientes en tiempo real. 

### Objetivos clave:
- **Respuesta consultiva y autorizada:** Responder como un Account Manager de TrackFlow en una llamada comercial con un cliente B2B, proporcionando información precisa y verificable.
- **Fidelidad y prevención de alucinaciones (Faithfulness):** Ningún porcentaje, plazo de SLA, transportista o tarifa puede diferir de la documentación oficial. Si la consulta no tiene fundamento en el corpus, el sistema declara con honestidad la falta de información.
- **Cumplimiento estricto de restricciones de negocio:**
  - Advertir sobre extensiones de plazo de hasta un 40% en picos de alta demanda (Black Friday, Navidad, Rebajas).
  - Remitir devoluciones internacionales a gestión manual con el equipo de Sofía Ramos.
  - Recordar que descuentos o tarifas preferenciales de almacenamiento (>50 m³) requieren aprobación de Miguel Torres.
  - Indicar que excepciones en asignación de transportistas requieren autorización de Carlos Vega.

---

## 2. Flujo del Proceso RAG de Extremo a Extremo

El flujo de procesamiento, indexación y consulta se estructura en capas desacopladas:

```
[Documentos Fuente Markdown] 
   docs/company-knowledge-base/
              │
              ▼
    [1. Chunking Semántico]
      data/process/rag.py
              │
              ▼
   [2. Ingesta & Embeddings]
       embed(chunk_text)
              │
              ▼
    [3. Vector DB Qdrant]
   Colección: trackflow_knowledge
              ▲
              │ Búsqueda Coseno (top-k, score >= min_score)
              │
    [4. retrieve(question)]
     data/pipelines/rag.py
              │
              ▼
 [5. generate_answer(question, context)]
     Prompt con voz de Account Manager
     LLM de generación (gpt-4o-mini)
              │
              ▼
     [6. query(question)]
       Respuesta final
              │
              ▼
 [7. Endpoint FastAPI & UI Backoffice]
  POST /knowledge/query -> Backoffice Next.js
```

### Etapas detalladas:
1. **Indexación (`setup`):** Lee los 4 documentos oficiales en `docs/company-knowledge-base/`, ejecuta la segmentación semántica (3 chunks por documento, 12 chunks en total), calcula vectores con `embed()` y crea la colección `trackflow_knowledge` en Qdrant con métrica de distancia Coseno e inserción idempotente mediante UUIDs deterministas (v5).
2. **Recuperación (`retrieve`):** Transforma la consulta del usuario en vector usando la misma función `embed()`, busca los $k$ vecinos más cercanos en Qdrant y descarta cualquier resultado cuya similitud caiga por debajo de `min_score`. Retorna únicamente los payloads limpios.
3. **Generación (`generate_answer`):** Construye un prompt enriquecido con los fragmentos recuperados y las restricciones de negocio de TrackFlow. Invoca al modelo de lenguaje generativo para formular una respuesta ejecutiva y cordial. Si el contexto está vacío, emite una respuesta honesta admitiendo la falta de información.
4. **Orquestación (`query`):** Punto de entrada unificado que encadena `retrieve` y `generate_answer`. Esta separación modular permite que futuros agentes autónomos (p. ej. LangGraph) reutilicen ambos pasos sin duplicar lógica ni reejecutar búsquedas.
5. **Consumo API & UI:** El router FastAPI expone `POST /knowledge/query` y el Backoffice Next.js proporciona una interfaz de consulta reactiva en `/knowledge` con soporte claro/oscuro y manejo de estados.

---

## 3. Estrategia de Chunking Semántico

Para el corpus de TrackFlow, fragmentar por número fijo de caracteres o tokens provocaría la ruptura de cláusulas contractuales, condiciones de compensación o tablas de tarifas. Por ello, se adoptó una **estrategia de segmentación semántica por unidad conceptual autocontenida**.

### Criterios aplicados:
- **Preservación de condiciones y excepciones:** Cada chunk agrupa una regla completa (por ejemplo, el compromiso del 90% de entregas a tiempo y su penalización del 5% forman un único chunk indivisible; las excepciones de Black Friday forman otro chunk independiente).
- **Mapeo del corpus (12 chunks en total, 3 por documento):**
  1. `sla-delivery`:
     - *Chunk 0:* Modalidades de envío (estándar, express, internacional) y tiempos estándar.
     - *Chunk 1:* Compromiso contractual de SLA (90% mensual) y compensación del 5% por 2 meses consecutivos caídos.
     - *Chunk 2:* Excepciones durante picos de alta demanda (Black Friday, Navidad, Rebajas: hasta +40% de tiempo).
  2. `returns-policy`:
     - *Chunk 0:* Flujo estándar de 3 pasos en logística inversa y clasificación en almacén.
     - *Chunk 1:* Ventana de devolución estándar (30 días) y distribución de costos (marca vs. TrackFlow).
     - *Chunk 2:* Devoluciones internacionales (gestión manual de Sofía Ramos) y política de no reacondicionamiento propio.
  3. `carrier-coverage`:
     - *Chunk 0:* Transportistas y cobertura en Estados Unidos (UPS, FedEx, DHL).
     - *Chunk 1:* Transportistas y cobertura en España (SEUR para Aragón rural, MRW para paquetes ligeros, locales en Zaragoza).
     - *Chunk 2:* Determinación automática por sistema de asignación y aprobación requerida de Carlos Vega para excepciones.
  4. `storage-pricing`:
     - *Chunk 0:* Tarifas base por metro cúbico (18 USD LA / 16 EUR Zaragoza) y periodo de gracia de 30 días.
     - *Chunk 1:* Recargo por inventario de larga duración (150% tras 180 días) y reportes de antigüedad.
     - *Chunk 2:* Condiciones para tarifas preferenciales (>50 m³) y aprobación obligatoria de Miguel Torres.

### Esquema del Payload en Qdrant:
```json
{
  "id": "uuid-v5-determinista",
  "vector": [ ... ],
  "payload": {
    "company": "trackflow",
    "source_document": "sla-delivery",
    "section": "SLA de Entrega - Excepciones en Picos de Alta Demanda (Black Friday / Rebajas)",
    "language": "es",
    "chunk_index": 2,
    "text": "TrackFlow no garantiza SLA de entrega los días de alta demanda declarados..."
  }
}
```

---

## 4. Prácticas de Embeddings y Modelos

### Separación de Responsabilidades en Modelos:
- **Modelo de Embeddings:** `text-embedding-3-small` (vectorización densa de 1536 dimensiones).
  - Utilizado de manera consistente tanto al indexar chunks en `setup()` como al vectorizar la consulta en `retrieve()`.
  - Normalización L2 aplicada para garantizar consistencia en la métrica Coseno.
- **Modelo de Generación:** `gpt-4o-mini` (o LLM compatible vía 4Geeks AI Gateway).
  - Empleado exclusivamente en `generate_answer()` para transformar el contexto y la consulta en texto natural en español con voz de Account Manager.
  - Se mantiene una separación estricta entre ambos IDs de modelo para optimizar costos, latencia y precisión semántica.

### Métrica de Distancia y Umbral de Similitud (`min_score`):
- **Métrica Qdrant:** `Distance.COSINE`.
- **Umbral de Similitud (`min_score = 0.35`):**
  - **Justificación:** Las consultas relevantes del dominio logístico arrojan similitudes superiores a 0.45 en vectores normalizados, mientras que consultas ajenas (ej. preguntas sobre cocina, deportes o temas no relacionados) caen por debajo de 0.25. El umbral de 0.35 proporciona un margen de seguridad óptimo: admite variaciones léxicas y sinonimia en preguntas comerciales legítimas, pero filtra categóricamente ruido externo impidiendo alucinaciones del modelo.

---

## 5. Resultados de Evaluación (Recall@3)

El pipeline fue evaluado mediante el dataset formal `data/eval/test-queries.json` compuesto por 10 preguntas de prueba representativas del negocio TrackFlow (cubriendo SLA, picos de alta demanda, devoluciones nacionales e internacionales, transportistas regionales y tarifas de almacenamiento):

| Métrica | Requisito CONTEXT | Resultado Obtenido | Estado |
| :--- | :---: | :---: | :---: |
| **Recall@3** | $\ge 80.00\%$ | **100.00%** (10/10) | **APROBADO** |
| Posición 1 del chunk | - | 100.00% (10/10) | Óptimo |

---

## 6. Mantenimiento y Extensibilidad

- **Idempotencia:** Al utilizar UUIDs deterministas v5 generados a partir de `trackflow:{source_doc}:{chunk_index}`, volver a ejecutar `setup()` actualiza o sobrescribe los puntos existentes sin duplicación de vectores.
- **Desacoplamiento para Agentes LangGraph:** La función `generate_answer(question, context)` y `retrieve(query)` están completamente desacopladas de `query()`, facilitando su integración en grafos de agentes con memoria conversacional y toma de decisiones multinivel.
