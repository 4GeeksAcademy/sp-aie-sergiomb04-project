## Objetivo

Auditar todo el monorepo y aplicar una estrategia consistente de gestión de errores en frontend, backend y scripts, sin añadir nuevas funcionalidades.

### Frontend

* Revisar todos los `fetch`/llamadas a la API y añadir `try/catch` específicos.
* Implementar el patrón de 3 estados en todas las operaciones asíncronas:

  * Loading.
  * Éxito.
  * Error con llamada a la acción (reintentar, volver al inicio o contactar soporte).
* Reemplazar errores técnicos por mensajes amigables.
* Usar `finally` para limpiar siempre el estado de carga.
* Aplicar `optional chaining (?.)` donde pueda haber `undefined`.
* Añadir valores por defecto (`fallbacks`) para `null` o `undefined`.

### Backend

* Revisar todos los endpoints y limitar los `try/except` a operaciones concretas.
* Devolver respuestas HTTP correctas (`400`, `404`, `422`, `500`) con JSON limpio.
* No exponer stack traces, rutas internas, claves ni información sensible.
* Añadir manejo de errores en llamadas a APIs externas o servicios de terceros.

### Scripts

* Proteger lectura/escritura de archivos y parseo de CSV con `try/except`.
* Mostrar errores informativos en `stderr`.
* Finalizar con `sys.exit(1)` ante errores críticos.
* Validar datos de entrada antes de procesarlos.

### General

* Eliminar o reemplazar `console.error` y `print` que expongan información sensible.
* No añadir funcionalidades nuevas ni hacer refactors fuera del manejo de errores.

### Requisitos

* Todas las operaciones asíncronas deben tener estados de carga, éxito y error.
* Todos los errores mostrados al usuario deben ser claros y ofrecer una acción.
* Los `try/catch` y `try/except` deben ser específicos, no envolver funciones completas.
* Usar `finally` para limpiar estados de carga.
* Evitar errores por `undefined` usando `?.` y valores por defecto.
* Todas las respuestas de error del backend deben ser limpias y seguras.
* Los scripts deben devolver un código de salida distinto de `0` cuando fallen.