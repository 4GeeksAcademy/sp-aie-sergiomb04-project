## Objetivo

Completa **toda** la tarea descrita en el README hasta cumplir todos los criterios de evaluación.

No simplifiques la implementación, no dejes TODOs, no generes código de ejemplo y no marques tareas como completadas sin haberlas realizado.

Debes trabajar directamente sobre el proyecto existente.

---

# Reglas obligatorias

* Analiza primero toda la estructura del proyecto antes de modificar nada.
* Identifica automáticamente:

  * endpoints de autenticación
  * servicios
  * utilidades
  * helpers
  * modelos
  * dependencias
  * tests existentes
* Mantén el estilo de código ya utilizado.
* No rompas funcionalidad existente.
* Si detectas un bug, arréglalo.
* Si una prueba revela un bug, primero corrige el código y luego deja el test.
* No elimines código salvo que sea estrictamente necesario.

---

# Orden de trabajo

## Fase 1

Analizar completamente el proyecto.

Identificar:

* estructura
* framework
* endpoints
* lógica de autenticación
* funciones auxiliares
* dependencias
* cobertura existente
* posibles problemas

No escribir código todavía.

---

## Fase 2

Crear un archivo

```
TESTING.md
```

Debe contener:

* objetivo
* cómo ejecutar las pruebas
* estructura de tests
* plan de pruebas
* cobertura esperada
* casos cubiertos por endpoint
* casos felices
* casos límite
* casos de fallo
* bugs encontrados
* bugs corregidos
* casos sugeridos por IA
* resultados finales de cobertura

Este documento debe actualizarse conforme avance el trabajo.

---

## Fase 3

Crear

```
tests/
```

si no existe.

Organizar los tests siguiendo la estructura del proyecto.

Ejemplo:

```
tests/
    test_register.py
    test_login.py
    test_token.py
    test_refresh.py
    test_logout.py
```

o cualquier organización equivalente si el proyecto utiliza otra estructura.

---

## Fase 4

Para **cada endpoint de autenticación** crear como mínimo:

### Camino feliz

Comprobar que la lógica funciona correctamente.

Ejemplos:

* registro correcto
* login correcto
* generación de token
* renovación de token
* logout correcto

---

### Casos límite

Buscar entradas válidas pero extremas.

Ejemplos:

* usuario ya existente
* contraseña vacía
* email vacío
* espacios
* longitud mínima
* longitud máxima
* mayúsculas/minúsculas
* caracteres especiales
* token justo antes de expirar
* token recién generado

Añadir cualquier otro caso que aplique al proyecto.

---

### Modos de fallo

Ejemplos:

* contraseña incorrecta
* usuario inexistente
* token expirado
* token inválido
* token malformado
* usuario deshabilitado
* petición inválida
* credenciales nulas

Añadir todos los casos relevantes.

---

# Qué probar

Probar únicamente lógica de negocio.

No probar:

* FastAPI
* serialización HTTP
* validación interna del framework
* routers
* Response
* Request
* Starlette
* Pydantic (salvo lógica propia)

No hacer tests que únicamente comprueben códigos HTTP.

Cada test debe verificar decisiones de negocio.

---

# Cobertura

Ejecutar:

```
uv run pytest
```

Corregir cualquier error.

Después ejecutar:

```
uv run pytest --cov
```

Objetivo:

**70% o superior**

Si la cobertura es inferior:

* localizar funciones sin cubrir
* añadir tests útiles
* volver a ejecutar

Repetir hasta superar el objetivo.

---

# Si existe TypeScript

Buscar automáticamente funciones relacionadas con autenticación.

Ejemplos:

* JWT
* helpers
* validadores
* hash
* almacenamiento
* parsers
* utilidades

Crear configuración de Jest si no existe.

Crear los tests necesarios.

Ejecutar:

```
jest --coverage
```

Corregir errores.

---

# Casos sugeridos por IA

Durante el desarrollo piensa en casos adicionales que normalmente un desarrollador olvidaría.

Por ejemplo:

* token manipulado
* token parcialmente válido
* email con espacios
* contraseña unicode
* múltiples logins
* renovación de token tras logout
* token de otro usuario
* expiración exacta
* usuario eliminado
* contraseña extremadamente larga

Añadir todos los que tengan sentido.

Documentarlos en TESTING.md.

---

# Bugs

Siempre que un test falle:

1. descubrir la causa
2. corregir el código
3. volver a ejecutar
4. comprobar que todo pasa
5. documentarlo

Nunca eliminar un test para que la suite pase.

---

# Calidad

Todos los tests deben:

* tener nombres descriptivos
* seguir el patrón Arrange / Act / Assert
* evitar duplicación
* reutilizar fixtures
* reutilizar helpers
* ser fáciles de leer
* incluir comentarios únicamente cuando aporten valor

---

# Extras

Si existe un backoffice:

Crear tests para al menos dos módulos.

Objetivo:

60% de cobertura.

---

Si existe frontend TypeScript:

Buscar al menos tres utilidades.

Crear dos tests por utilidad:

* camino feliz
* modo de fallo

Actualizar TESTING.md con instrucciones independientes.

---

# Verificación final

Antes de finalizar comprobar:

* TESTING.md existe
* tests/ existe
* todos los tests pasan
* pytest pasa sin errores
* cobertura >=70%
* Jest pasa (si aplica)
* no quedan TODO
* no quedan FIXME
* no quedan pruebas rotas
* no queda código muerto generado durante el desarrollo

---

# Entrega

La tarea solo se considera terminada cuando se cumplen todos los requisitos del README y todos los criterios de evaluación.

No des la tarea por finalizada mientras exista cualquier requisito sin implementar. Continúa trabajando hasta completar absolutamente todo.
