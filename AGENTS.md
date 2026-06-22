# AGENTS.md - Guia Operativa del Monorepo TrackFlow

## 1) Proposito del agente
Este monorepo soporta la transformacion digital de TrackFlow Tech para operaciones logisticas en dos paises. Cualquier cambio debe aportar a uno o mas objetivos de negocio:

- Mayor visibilidad operativa en tiempo real.
- Menos trabajo manual y menos errores.
- Mejor experiencia de cliente B2B y B2C.
- Mejor capacidad de decision basada en datos.
- Escalabilidad y operacion 24/7.

Si una tarea no contribuye de forma clara a estos objetivos, debe replantearse antes de implementarse.

## 2) Lectura obligatoria al iniciar cada sesion
Antes de proponer cambios o escribir codigo, el agente debe leer en este orden:

1. memory-bank/projectbrief.md
2. memory-bank/techContext.md
3. memory-bank/progress.md

Objetivo de esta lectura:

- Alinear la solucion con el contexto empresarial real.
- Respetar restricciones tecnicas y arquitectura del monorepo.
- Evitar retrabajo y duplicacion de esfuerzos respecto al estado actual.

Si falta alguno de estos archivos o esta desactualizado, el agente debe reportarlo y proponer actualizacion antes de continuar con cambios grandes.

## 3) Flujo obligatorio antes de cada commit
No se permite saltar este flujo. Debe ejecutarse de forma secuencial y documentada en el mensaje de trabajo o PR.

### Paso 1 - Validacion de contexto y alcance
- Revisar objetivo funcional y su impacto en operaciones de TrackFlow.
- Confirmar en que hito encaja el cambio (estado actual: Hito 4 en curso).
- Identificar modulos afectados y dependencias.

### Paso 2 - Verificacion tecnica local
- Ejecutar chequeos de calidad segun corresponda al area modificada: lint, tipos, build y pruebas.
- Verificar que no se rompan flujos clave del dominio (listado, detalle, estado/etapa, notas en app activa).
- Revisar errores de consola y estados de carga/error en UI cuando aplique.

### Paso 3 - Revision de impacto de negocio
- Comprobar que el cambio mejora al menos una metrica o capacidad operativa.
- Validar que no degrada trazabilidad, observabilidad o consistencia de datos.
- Confirmar que mantiene compatibilidad con evolucion futura hacia APIs de inventario, tracking y devoluciones.

### Paso 4 - Actualizacion de memoria del proyecto
- Actualizar memory-bank/progress.md con estado real del avance.
- Si hubo decisiones de arquitectura o restricciones nuevas, actualizar memory-bank/techContext.md.
- Si cambia alcance de negocio, stakeholders o prioridades, actualizar memory-bank/projectbrief.md.

### Paso 5 - Revision de diff y limpieza final
- Inspeccionar cambios para evitar ediciones accidentales fuera de alcance.
- Eliminar codigo temporal, logs de depuracion y texto placeholder.
- Verificar consistencia de nombres, tipos y contratos.

### Paso 6 - Commit trazable
- Redactar commit con formato claro: area + accion + objetivo.
- Incluir referencia corta al impacto esperado en TrackFlow.

## 4) Rutas protegidas: no modificar sin confirmacion explicita
Las siguientes rutas requieren confirmacion explicita previa del usuario o responsable tecnico:

- CONTEXT.md
- company-choice.md
- memory-bank/projectbrief.md
- memory-bank/techContext.md
- apps/talent-pipeline-tracker/TASK.md
- apps/talent-pipeline-tracker/package.json
- packages/shared/package.json
- packages/shared/types/index.ts

Tambien requieren confirmacion explicita:

- Borrado o renombrado de carpetas de primer nivel del monorepo.
- Cambios masivos de estructura en apps, packages, data o workflows.
- Cualquier cambio que altere contratos compartidos entre apps y paquete shared.

## 5) Politicas de implementacion para TrackFlow

### 5.1 Priorizacion funcional
Priorizar tareas con impacto directo en:

- Operacion de almacen: inventario, alertas, flujo de pedidos.
- Ultima milla: tracking unificado y calidad de asignacion de carrier.
- Logistica inversa: tiempos y consistencia del flujo de devoluciones.
- CX: tiempos de respuesta y reduccion de consultas manuales.
- Direccion: disponibilidad de indicadores confiables y actualizados.

### 5.2 Calidad minima esperada
- Todo cambio debe contemplar estados de carga, exito y error.
- Evitar acoplamiento innecesario entre UI, servicios y tipos.
- Mantener tipado claro y contratos consistentes.
- Favorecer componentes y utilidades reutilizables.

### 5.3 Observabilidad y trazabilidad
- Cualquier integracion nueva debe prever logging util para soporte.
- Errores de API deben ser accionables y comprensibles.
- Evitar flujos silenciosos sin feedback para usuario interno.

## 6) Buenas practicas para mantener actualizado el memory-bank

### Frecuencia
- Actualizar al cerrar una tarea relevante o antes de cada commit importante.
- No esperar al final del sprint si hubo decisiones significativas.

### Reglas de contenido
- Escribir resumenes breves, concretos y verificables.
- Registrar decisiones, riesgos y siguientes pasos accionables.
- Evitar texto promocional o ambiguo.
- Mantener coherencia entre projectbrief, techContext y progress.

### Criterios por archivo
- projectbrief.md: solo cambios de negocio, objetivos o stakeholders.
- techContext.md: arquitectura, restricciones, integraciones, decisiones tecnicas.
- progress.md: estado real, hitos, bloqueos, siguiente accion prioritaria.

### Anti-patrones a evitar
- Marcar hitos como completados sin evidencia tecnica.
- Duplicar contenido identico en los tres archivos.
- Dejar tareas en curso sin fecha o sin siguiente paso.

## 7) Definicion de listo para merge
Un cambio esta listo para merge cuando:

- Cumple el flujo pre-commit completo.
- No toca rutas protegidas sin autorizacion.
- Mantiene alineacion con objetivos de TrackFlow.
- Deja actualizado el memory-bank segun el impacto real.
- Puede ser entendido y continuado por otro agente sin contexto adicional.
