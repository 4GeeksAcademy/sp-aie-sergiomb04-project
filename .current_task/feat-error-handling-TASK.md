## Objetivo

Completa este proyecto auditando y corrigiendo **únicamente** la gestión de errores del monorepo existente. No añadas funcionalidades ni hagas refactors innecesarios. Implementa una estrategia consistente en frontend, backend y scripts para que todos los errores sean controlados, seguros y útiles para el usuario.

## Reglas

- Trabaja directamente sobre el código existente.
- Haz los cambios mínimos necesarios.
- Mantén el estilo y arquitectura del proyecto.
- No rompas funcionalidades existentes.
- Si detectas un problema, corrígelo en lugar de dejar comentarios TODO.

## Tareas

### Frontend (Next.js / TypeScript)

- [ ] Añadir `try/catch` a todas las llamadas `fetch` o API.
- [ ] Implementar estados **loading**, **success** y **error** en toda carga asíncrona.
- [ ] Mostrar mensajes de error claros, nunca errores técnicos.
- [ ] Añadir una acción al usuario en cada error (Reintentar, Inicio o Contacto).
- [ ] Usar `finally` para limpiar estados de carga.
- [ ] Aplicar `optional chaining (?.)` donde sea necesario.
- [ ] Añadir valores por defecto (`??` o fallbacks) para evitar `undefined` o `null`.

### Backend (FastAPI)

- [ ] Limitar cada `try/except` únicamente a la operación que puede fallar.
- [ ] Devolver respuestas JSON limpias con códigos HTTP adecuados.
- [ ] No exponer stack traces ni información sensible.
- [ ] Manejar correctamente errores de APIs externas.

### Scripts (Python)

- [ ] Manejar errores de lectura/escritura y parseo mediante `try/except`.
- [ ] Escribir errores en `stderr`.
- [ ] Finalizar con `sys.exit(1)` ante errores críticos.
- [ ] Validar entradas antes de procesarlas.

### General

- [ ] Eliminar `console.error` y `print` que expongan información sensible.
- [ ] Mantener una estrategia de gestión de errores consistente en todo el repositorio.

## Criterios de finalización

- No existen operaciones asíncronas sin manejo de errores.
- Toda carga tiene estados loading/success/error.
- Ningún usuario ve mensajes técnicos o stack traces.
- Ninguna respuesta expone información sensible.
- Todos los scripts terminan correctamente con códigos de salida apropiados.
- El proyecto compila y todas las funcionalidades existentes siguen funcionando.