# Skill: Feature Validation

## Descripcion
Valida una funcionalidad antes de realizar un commit en el monorepo de TrackFlow.

Esta skill asegura que los cambios:
- no duplican logica de negocio,
- respetan las reglas y convenciones del monorepo,
- cumplen los requisitos funcionales solicitados,
- y dejan la documentacion relevante actualizada para continuidad del equipo y de otros agentes.

## Inputs requeridos
1. Requisitos de la funcionalidad
- Descripcion funcional recibida.
- Criterios de exito esperados por el solicitante.

2. Alcance tecnico
- Lista de archivos modificados.
- Modulos afectados y dependencias principales.

3. Evidencia de verificacion
- Resultado de lint, tipos, build y pruebas aplicables.
- Evidencia de pruebas manuales (si aplica UI o flujo de usuario).

4. Contexto del monorepo
- AGENTS.md.
- .agents/rules/no-business-logic-duplication.md.
- memory-bank/projectbrief.md.
- memory-bank/techContext.md.
- memory-bank/progress.md.

## Pasos a seguir
### Paso 1: Confirmar contexto y alcance
- Leer los requisitos y convertirlos en checklist verificable.
- Identificar que parte del negocio de TrackFlow impacta el cambio (operaciones, ultima milla, devoluciones, CX, comercial o direccion).
- Confirmar que el alcance tecnico coincide con los archivos realmente modificados.

### Paso 2: Revisar duplicacion de logica de negocio
- Buscar implementaciones equivalentes en rutas compartidas:
  - packages/shared/
  - src/utils/
  - src/types/
  - uis/*/app/features/**/lib/
  - uis/*/app/features/**/services/
  - uis/*/app/features/**/types/
- Verificar que no existan nuevas funciones que repliquen reglas ya implementadas con otro nombre.
- Si hubo nueva logica transversal, confirmar que se extrajo a modulo reutilizable.

### Paso 3: Validar cumplimiento de reglas del monorepo
- Verificar alineacion con AGENTS.md y reglas en .agents/rules/.
- Confirmar que no se tocaron rutas protegidas sin confirmacion explicita.
- Confirmar separacion correcta por capas (UI, servicios, tipos, utilidades compartidas).

### Paso 4: Verificar cumplimiento de requisitos funcionales
- Revisar cada requisito recibido contra evidencia tecnica real.
- Ejecutar o revisar resultados de lint, tipos, build y pruebas.
- Validar estados esperados: carga, exito, error y manejo de casos borde relevantes.

### Paso 5: Validar documentacion y memoria del proyecto
- Confirmar si el cambio exige actualizar:
  - memory-bank/progress.md,
  - memory-bank/techContext.md,
  - memory-bank/projectbrief.md.
- Verificar que cualquier decision tecnica relevante quedo documentada.
- Confirmar trazabilidad entre implementacion y documentacion.

### Paso 6: Emitir veredicto pre-commit
- Emitir estado final: PASS o FAIL.
- Si FAIL, listar bloqueos y acciones exactas para resolverlos antes del commit.
- Si PASS, listar resumen corto de evidencia validada.

## Output esperado
Un informe de validacion pre-commit con la siguiente estructura:

- Resumen de funcionalidad validada.
- Estado final: PASS o FAIL.
- Checklist por criterio (cumple/no cumple) con evidencia concreta.
- Riesgos detectados y severidad.
- Acciones pendientes obligatorias antes de commit (si existen).

Formato recomendado:

1. Funcionalidad validada
2. Resultado final
3. Evidencia por criterio
4. Riesgos
5. Acciones requeridas

## Acceptance Criteria verificables
La skill solo aprueba cuando todos los criterios siguientes son verdaderos:

1. No existe logica de negocio duplicada
- Se realizo busqueda en rutas compartidas.
- No hay implementaciones nuevas que repitan reglas existentes.
- Si hubo logica comun nueva, esta centralizada en modulo reutilizable.

2. Se respetan las reglas del monorepo
- Los cambios son consistentes con AGENTS.md y reglas activas.
- No se modificaron rutas protegidas sin confirmacion explicita.
- La arquitectura del cambio mantiene separacion de responsabilidades.

3. La funcionalidad cumple los requisitos recibidos
- Cada requisito tiene evidencia de implementacion o prueba.
- Las validaciones tecnicas aplicables (lint, tipos, build, pruebas) estan en estado correcto.
- Los flujos principales y casos borde definidos fueron revisados.

4. La documentacion relevante esta actualizada
- Se actualizo la documentacion afectada por el cambio.
- Se actualizaron archivos del memory-bank cuando hubo impacto en estado, contexto tecnico o alcance de negocio.
- La informacion publicada es coherente con el codigo entregado.

## Regla de bloqueo
Si falla cualquier Acceptance Criteria, el commit debe bloquearse hasta corregir la desviacion y volver a ejecutar esta skill.