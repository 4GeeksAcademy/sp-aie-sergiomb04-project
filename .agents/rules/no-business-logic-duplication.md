# Regla: No Business Logic Duplication

## Nombre
No Business Logic Duplication

## Proposito
Evitar la duplicacion de logica de negocio en el monorepo de TrackFlow para mantener consistencia funcional, reducir errores y acelerar mantenimiento. Esta regla protege especialmente dominios criticos como inventario, tracking multicarrier, devoluciones, scoring y validaciones operativas.

## Alcance
Always Active

## Regla
- No duplicar logica de negocio que ya exista en el repositorio.
- Antes de crear una implementacion nueva, buscar y reutilizar modulos existentes en rutas compartidas.
- Si no existe un modulo reutilizable, extraer la logica a un modulo compartido en lugar de copiarla en multiples apps o componentes.
- Toda nueva logica de negocio debe quedar en una capa reutilizable (servicio, util o paquete compartido), no embebida en UI cuando pueda ser compartida.

## Fuentes de reutilizacion obligatoria (TrackFlow)
Revisar primero estas ubicaciones antes de implementar algo nuevo:

- packages/shared/
- src/utils/
- src/types/
- uis/*/app/features/**/lib/
- uis/*/app/features/**/services/
- uis/*/app/features/**/types/

Si existe una funcion equivalente o compatible, debe reutilizarse o extenderse. No se permite reescribir la misma regla de negocio con otro nombre.

## Comportamiento incorrecto
### Ejemplo 1: Duplicar scoring de transportista
- Ya existe una logica de scoring/seleccion de carrier en modulos de utilidades.
- Se crea otra funcion nueva en un componente de UI con formulas parecidas para elegir transportista.
- Resultado: dos criterios distintos para la misma decision de negocio.

### Ejemplo 2: Repetir validaciones de devoluciones en cada app
- Se implementan validaciones similares de devolucion en varios formularios de apps distintas.
- Cada equipo aplica umbrales diferentes para aprobacion.
- Resultado: inconsistencias operativas entre paises y mayor tasa de errores.

### Ejemplo 3: Copiar normalizacion de estados en multiples archivos
- Se copia y pega el mismo mapeo de estados (pending, approved, rejected, etc.) en varios servicios.
- Resultado: cuando cambia una regla, se rompe la sincronizacion del sistema.

## Comportamiento correcto
### Ejemplo 1: Reutilizar modulo existente
- Se necesita calcular scoring de carrier para ultima milla.
- Se reutiliza la funcion existente en utilidades/servicios compartidos.
- Si falta un criterio, se extiende ese modulo y se mantiene una sola fuente de verdad.

### Ejemplo 2: Extraer logica comun de devoluciones
- Se detecta que dos apps aplican la misma regla de aprobacion de devoluciones.
- En lugar de duplicar, se crea o mueve la logica a un modulo compartido y ambas apps lo consumen.

### Ejemplo 3: Centralizar transformaciones de estado
- Se identifica mapeo repetido de estados de tracking en varios puntos.
- Se centraliza en una utilidad compartida y se reemplazan las copias locales.

## Criterios de cumplimiento antes de merge
- Se realizo busqueda previa de implementaciones existentes en rutas compartidas.
- No quedaron bloques de negocio duplicados en componentes o servicios nuevos.
- Si hubo nueva logica transversal, fue extraida a modulo reutilizable.
- Los cambios mantienen coherencia funcional para objetivos de TrackFlow: operacion 24/7, consistencia multinacional y decision basada en datos.
