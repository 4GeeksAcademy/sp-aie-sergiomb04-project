# Implementación completa de práctica en monorepo

Actúa como un Senior Full Stack Engineer especializado en FastAPI, TinyDB, Pydantic y React.

Vas a implementar completamente esta práctica dentro del monorepo existente. NO crees un proyecto nuevo.

## IMPORTANTE

Antes de escribir una sola línea de código:

1. Localiza y lee completamente el archivo [CONTEXT-company.md](.current_task/CONTEXT-trackflow.es.md).
2. Extrae de él:
   - todos los campos exactos del modelo `Supplier`
   - el nombre exacto del campo de tarifa
   - categorías válidas
   - estados permitidos
   - datos iniciales para el seeder

**NO** inventes nombres de campos.  
**NO** utilices valores genéricos.  
**TODO** debe coincidir exactamente con el `CONTEXT`.

Si el contexto es demasiado grande para una sola respuesta, divide automáticamente el trabajo en varias fases.

---

# PLAN DE TRABAJO

## Fase 1

- Analizar el proyecto.
- Leer `CONTEXT-company.md`.
- Inspeccionar la estructura del monorepo.
- Identificar dónde está FastAPI.
- Identificar dónde está el frontend.
- Mostrar un pequeño plan antes de modificar código.

Esperar únicamente si falta información imprescindible.

Si toda la información existe en el repositorio, continuar automáticamente.

---

## Fase 2

### Backend

Crear toda la estructura necesaria.

Implementar:

- `database.py`
- `models.py`
- `routes/suppliers.py`
- `seed.py`
- Actualizar `main.py`

Debe existir:

- `POST /suppliers`
- `GET /suppliers`
- `GET /suppliers/{id}`
- `PATCH /suppliers/{id}/rate`
- `PATCH /suppliers/{id}/status`
- `DELETE /suppliers/{id}`

### Requisitos

- Usar TinyDB.
- Persistencia real.
- Modelos Pydantic.
- Modelos separados para entrada y salida cuando sea necesario.
- `updated_at` generado automáticamente.
- `status` usando `Enum` o validación.
- La tarifa debe ser `> 0`.

Errores HTTP correctos:

- `422`
- `404`
- `200`
- `201`

Implementar filtros:

- `GET /suppliers?country=`
- `GET /suppliers?category=`

---

## Fase 3

### Seeder

Crear `seed.py`.

Debe funcionar con:

```bash
uv run seed
```

Debe:

- leer los proveedores del `CONTEXT`
- insertarlos
- evitar duplicados

Mostrar:

```text
Inserted X suppliers
```

Si ya existen, no duplicarlos.

---

## Fase 4

### Frontend

Dentro de:

```text
uis/backoffice
```

Crear la página **Suppliers**.

Agregar entrada al menú.

Implementar:

- tabla
- filtros
- alta
- editar tarifa
- editar estado
- badges para activo/suspendido
- actualización inmediata después de las llamadas a la API
- mostrar errores `422` enviados por la API
- no recargar la página para filtrar

---

## Fase 5

### Validación

Comprobar que absolutamente todos los requisitos del README están cumplidos.

Crear una checklist indicando:

- ✔ realizado
- ⚠ pendiente
- ❌ falta

No marcar como realizado algo que realmente no exista.

---

# REGLAS

- No romper código existente.
- Reutilizar componentes si existen.
- Seguir el estilo del proyecto.
- No duplicar lógica.
- Escribir código limpio.
- Usar typing.
- Añadir comentarios solo cuando aporten valor.
- No generar archivos innecesarios.
- Si encuentras una estructura ya existente, intégrate en ella.

Al terminar cada fase:

- verifica que compile
- corrige errores automáticamente
- continúa con la siguiente fase

Solo detente cuando toda la práctica esté completamente implementada.

El objetivo es completar las **44 tareas del README**.