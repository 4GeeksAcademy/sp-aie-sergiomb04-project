# CACHING_REPORT

## Frontend - Lazy Loading

### Componentes/rutas elegidos

1. `uis/backoffice/app/(protected)/incidents/page.tsx`
   - `IncidentUploadPanel` cargado con `next/dynamic`.
   - `IncidentSummaryPanel` cargado con `next/dynamic`.
2. `uis/backoffice/app/(protected)/suppliers/page.tsx`
   - `SuppliersPanel` cargado con `next/dynamic`.

### Motivo de cada elección

- `IncidentUploadPanel`:
  - Incluye flujo de subida/análisis CSV y no es imprescindible para ver listado inicial.
  - Es un bloque funcional separado y diferible sin romper UX.
- `IncidentSummaryPanel`:
  - Hace llamada dedicada a resumen y se puede cargar después del contenido principal.
- `SuppliersPanel`:
  - Es una vista cliente con lógica extensa (formularios, autosave, estados locales).
  - Diferir su bundle reduce trabajo inicial de parse/evaluación JS al entrar en ruta protegida.

### Impacto medido o estimado

- Medición directa de tamaño de chunks no disponible en esta tarea (no había baseline de bundle previo instrumentado en CI).
- Impacto estimado:
  - Menor JS crítico inicial en rutas protegidas donde estos paneles no son necesarios para el primer paint.
  - Menor coste de hidratación inicial en navegación a incidentes/proveedores.

## Frontend - useMemo

### Cálculo elegido

Archivo: `uis/backoffice/app/features/suppliers/components/SuppliersPanel.tsx`

Se añadió `useMemo` para derivar `supplierTableRows`:
- unión de categorías en label por fila,
- formateo de tarifa por fila,
- formateo de fecha (`Intl.DateTimeFormat`) por fila.

### Por qué es costoso

- El formateo con `Intl` y concatenaciones por cada proveedor se repite en cada render, incluso cuando cambia estado no relacionado (modal, mensajes, edición de inputs).
- Con más proveedores (post-seeding), la recomputación de todas las filas escala linealmente y se vuelve perceptible.

### Dependencias

- Dependencia única: `suppliers`.

### Beneficio medido/estimado

- Beneficio estimado: evita recomputar mapeo/formateo de toda la tabla cuando cambian estados locales que no alteran el dataset base.
- Resultado esperado: menor tiempo de render/re-render en interacciones de formulario y autosave.

## Backend - Endpoints analizados

| Endpoint | Coste | Frecuencia esperada | Estabilidad de datos | Decisión |
|---|---:|---:|---|---|
| GET /suppliers | Medio (lectura + filtros TinyDB) | Alta en panel proveedores | Media-alta | Cachear |
| GET /suppliers/{id} | Bajo-medio | Media | Media | Cachear |
| GET /api/incidents | Medio (lectura + filtros en memoria) | Alta en listado incidencias | Media | Cachear |
| GET /api/incidents/summary | Medio (agregaciones por status/categoría/origen/sede) | Alta en dashboard incidencias | Media | Cachear |
| GET /api/incidents/results/export | Bajo (devuelve último CSV en memoria) | Baja-media | Baja (resultado cambia tras analyze) | No cachear |
| GET /auth/me | Bajo | Alta | Baja (datos de sesión/identidad) | No cachear |
| GET /users, GET /users/{id} | Bajo-medio | Baja-media | Baja-media | No cachear (fuera de foco de rendimiento actual) |
| GET /profiles/me | Bajo | Media | Baja (perfil del usuario) | No cachear |
| GET /inventory/products | Alto (cálculo de stock) | Alta | Media | No cacheado en este cambio (pendiente siguiente iteración) |
| GET /inventory/products/{id} | Medio | Media | Media | No cacheado en este cambio |
| GET /inventory/orders | Medio-alto (join + ordenación) | Media | Baja-media | No cacheado en este cambio |

## Backend - Endpoints cacheados

### Estrategia

- Caché en memoria con TTL reutilizable (`services/api/trackflow_api/cache.py`).
- Middleware de timing (`X-Process-Time-Ms`) para medir latencia por request.

### Endpoints

1. `GET /suppliers`
   - Clave: `suppliers:list:user={user_id}:country={country|all}:category={category|all}`
   - TTL: 45s
   - Motivo TTL: directorio relativamente estable, pero con necesidad de reflejar cambios operativos sin mucha demora.
   - Invalidación:
     - `POST /suppliers`
     - `PATCH /suppliers/{id}/rate`
     - `PATCH /suppliers/{id}/status`
     - `DELETE /suppliers/{id}`
     - patrón invalidado: prefijo `suppliers:`
   - Latencia (benchmark local con dataset seed):
     - miss promedio: 1.68 ms
     - hit promedio: 1.43 ms
     - mejora estimada: 14.84%

2. `GET /suppliers/{id}`
   - Clave: `suppliers:detail:user={user_id}:supplier_id={supplier_id}`
   - TTL: 30s
   - Motivo TTL: detalle cambia por acciones explícitas (rate/status) y se invalida en escrituras.
   - Invalidación: mismo prefijo `suppliers:` en operaciones de escritura.
   - Latencia: mejora esperada similar a listados de detalle repetido (no se midió aislado en este informe).

3. `GET /api/incidents`
   - Clave: `incidents:list:user={user_id}:status={...}:origin={...}:branch={...}:category={...}`
   - TTL: 20s
   - Motivo TTL: alto patrón de lectura/re-filtro en UI con datos que cambian por eventos discretos.
   - Invalidación:
     - `POST /api/incidents`
     - `PATCH /api/incidents/{id}/status`
     - patrón invalidado: prefijo `incidents:`
   - Latencia:
     - miss promedio: 3.40 ms
     - hit promedio: 2.98 ms
     - mejora estimada: 12.20%

4. `GET /api/incidents/summary`
   - Clave: `incidents:summary:user={user_id}`
   - TTL: 30s
   - Motivo TTL: resumen agregado con alto coste relativo y buena reutilización entre refrescos cercanos.
   - Invalidación: mismo prefijo `incidents:` tras create/update.
   - Latencia:
     - miss promedio: 2.33 ms
     - hit promedio: 1.10 ms
     - mejora estimada: 52.64%

## Datos de prueba

- Incidencias antes del seeding (entorno aislado de benchmark): 0
- Incidencias insertadas por seeder: 240
- Incidencias tras seeding: 240

Seeder utilizado:
- `services/api/trackflow_api/seed_incidents.py`

Efecto del seeding en mediciones:
- Incrementó coste de filtros y agregaciones de incidencias, permitiendo observar mejor la diferencia miss/hit.
- Evitó conclusiones con datasets triviales.

## Trade-off frescura vs rendimiento

Ejemplo concreto:
- `GET /api/incidents/summary` con TTL de 30s.

Justificación:
- El resumen es agregado y suele consultarse repetidamente en intervalos cortos.
- Aceptar hasta 30s de posible obsolescencia reduce trabajo repetido de agregación.
- La invalidación inmediata tras create/update minimiza el riesgo de stale prolongado.

## Qué NO se cacheó

Candidato descartado:
- `GET /auth/me`

Motivo técnico:
- Respuesta ligada a identidad/sesión de usuario.
- Aunque se podrían usar claves por usuario, el beneficio es bajo y el riesgo de errores de diseño de clave en autenticación es alto comparado con endpoints de negocio agregados/listados.

Otros no cacheados en esta iteración:
- Endpoints de inventario (`/inventory/products`, `/inventory/orders`, etc.).
- Son buenos candidatos por coste, pero se dejaron para una siguiente iteración para mantener el alcance acotado y validar primero seguridad/invalidación en dominios de incidencias y proveedores.
