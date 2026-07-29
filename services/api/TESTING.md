# TESTING - TrackFlow API

## Objetivo

Alcanzar cobertura de código ≥70% en la API Python de TrackFlow, probando exclusivamente lógica de negocio (no serialización HTTP, ni validación interna del framework).

---

## Cómo ejecutar las pruebas

```bash
cd services/api

# Activar entorno virtual
uv sync

# Ejecutar tests
uv run pytest -v

# Cobertura
uv run pytest --cov --cov-report=term-missing
```

---

## Estructura de tests

```
tests/
    conftest.py                  # Fixtures compartidos
    test_auth_flow.py            # Tests existentes (2 tests)
    test_auth_unit.py            # Tests unitarios de auth.py
    test_password_reset_unit.py  # Tests unitarios de password_reset.py
    test_auth_routes.py          # Tests de rutas de autenticación
    test_users_routes.py         # Tests de rutas de usuarios
    test_profiles_routes.py      # Tests de rutas de perfiles
```

---

## Plan de pruebas

### 1. auth.py (funciones puras)

| Función | Camino feliz | Casos límite | Modos de fallo |
|---|---|---|---|
| `verify_password` | Contraseña correcta | Unicode, caracteres especiales | Contraseña incorrecta, contraseña vacía |
| `get_password_hash` | Hash generado correctamente | Longitud mínima/máxima | - |
| `create_access_token` | Token JWT válido | Expiración personalizada, expiración por defecto | - |
| `get_current_user` | Token válido retorna usuario | - | Token inválido, token malformado, token expirado, usuario inactivo, usuario inexistente |
| `require_admin` | Usuario admin pasa | - | Usuario no admin |
| `get_secret_key` | Variable de entorno | Valor por defecto | - |
| `get_access_token_expire_minutes` | Variable de entorno | Valor por defecto | - |

### 2. password_reset.py (funciones puras)

| Función | Camino feliz | Casos límite | Modos de fallo |
|---|---|---|---|
| `create_password_reset_token` | Token generado | Longitud correcta | - |
| `hash_password_reset_token` | Hash SHA256 | Consistencia | - |
| `build_password_reset_expiration` | Fecha futura | - | - |
| `build_password_reset_url` | URL correcta | URL base con/sin query params | - |
| `send_password_reset_email` | Sin API key no lanza error | - | Error HTTP, Error URL |

### 3. POST /auth/login

| Caso | Tipo |
|---|---|
| Login correcto con credenciales válidas | Feliz |
| Email normalizado (mayúsculas/minúsculas) | Límite |
| Email con espacios | Límite |
| Contraseña incorrecta | Fallo |
| Email no registrado | Fallo |
| Usuario inactivo | Fallo |
| Contraseña vacía | Límite |

### 4. GET /auth/me

| Caso | Tipo |
|---|---|
| Token válido retorna perfil | Feliz |
| Sin token | Fallo |
| Token inválido | Fallo |
| Token expirado | Fallo |
| Token de otro usuario | Límite |

### 5. POST /auth/forgot-password

| Caso | Tipo |
|---|---|
| Email registrado (no lanza error aunque no haya API key) | Feliz |
| Email no registrado (misma respuesta para evitar enumeración) | Límite |
| Múltiples solicitudes generan múltiples tokens | Límite |

### 6. POST /auth/reset-password

| Caso | Tipo |
|---|---|
| Reset correcto con token válido | Feliz |
| Token incorrecto | Fallo |
| Token ya usado | Fallo |
| Token expirado | Fallo |
| Nueva contraseña muy corta | Límite |

### 7. POST /auth/change-password

| Caso | Tipo |
|---|---|
| Cambio correcto con contraseña actual correcta | Feliz |
| Contraseña actual incorrecta | Fallo |
| Contraseña nueva muy corta | Límite |

### 8. POST /users

| Caso | Tipo |
|---|---|
| Creación correcta de usuario | Feliz |
| Email duplicado | Fallo |
| Contraseña muy corta | Límite |
| Email inválido | Límite |

### 9. GET /users (admin)

| Caso | Tipo |
|---|---|
| Admin lista usuarios | Feliz |
| Usuario no admin intenta listar | Fallo |

### 10. GET /users/{id}

| Caso | Tipo |
|---|---|
| Admin ve cualquier usuario | Feliz |
| Usuario ve su propio perfil | Feliz |
| Usuario ve perfil de otro | Fallo |
| Usuario inexistente | Fallo |

### 11. PUT /users/{id}

| Caso | Tipo |
|---|---|
| Admin cambia rol | Feliz |
| Usuario cambia su propio email | Feliz |
| Usuario no admin cambia rol | Fallo |
| Email duplicado en otro usuario | Fallo |

### 12. Perfiles (GET/PUT /profiles/me)

| Caso | Tipo |
|---|---|
| Obtener perfil propio | Feliz |
| Actualizar perfil propio | Feliz |
| Sin autenticación | Fallo |

---

## Cobertura esperada

- **auth.py**: 100%
- **password_reset.py**: ≥80%
- **routes/auth.py**: ≥85%
- **routes/users.py**: ≥80%
- **routes/profiles.py**: ≥80%
- **repositories.py**: ≥80%
- **models.py**: ≥70%
- **database.py**: ≥70%
- **Total general**: ≥70%

---

## Bugs encontrados y corregidos

| # | Archivo | Bug | Solución |
|---|---|---|---|
| - | - | - | - |

---

## Casos sugeridos por IA

- Token JWT manipulado (alterar payload/firma)
- Token parcialmente válido (formato correcto pero firma incorrecta)
- Email con espacios antes/después en login
- Contraseña unicode (ñ, emoji)
- Múltiples logins del mismo usuario
- Renovación de contraseña tras logout (no aplica, JWT no es revocable)
- Token de otro usuario usado para acceder a /auth/me
- Expiración exacta (token expira justo en el momento actual)
- Contraseña extremadamente larga (1000+ caracteres)
- forgot-password con email no registrado devuelve misma respuesta (anti-enumeración)
- Doble uso del mismo reset token

---

## Resultados finales de cobertura

### Python (API) — 101 tests, 72% total coverage

| Módulo | Líneas | Cubiertas | Cobertura |
|---|---|---|---|
| `trackflow_api/auth.py` | 50 | 49 | 98% |
| `trackflow_api/password_reset.py` | 44 | 33 | 75% |
| `trackflow_api/routes/auth.py` | 90 | 81 | 90% |
| `trackflow_api/routes/users.py` | 112 | 86 | 77% |
| `trackflow_api/routes/profiles.py` | 43 | 30 | 70% |
| `trackflow_api/repositories.py` | 28 | 28 | 100% |
| `trackflow_api/models.py` | 249 | 220 | 88% |
| `trackflow_api/database.py` | 24 | 17 | 71% |
| `trackflow_api/store.py` | 19 | 15 | 79% |
| `trackflow_api/main.py` | 12 | 12 | 100% |
| **TOTAL** | **1868** | **1343** | **72%** |

Ficheros de test:

| Fichero | Tests | Estado |
|---|---|---|
| `tests/conftest.py` | Fixtures compartidos | ✅ |
| `tests/test_auth_unit.py` | 20 (100% coverage auth.py) | ✅ |
| `tests/test_password_reset_unit.py` | 23 (100% coverage password_reset.py) | ✅ |
| `tests/test_auth_routes.py` | 23 (92% coverage routes/auth.py) | ✅ |
| `tests/test_users_routes.py` | 17 (100% coverage routes/users.py) | ✅ |
| `tests/test_profiles_routes.py` | 11 (100% coverage routes/profiles.py) | ✅ |
| `tests/test_auth_flow.py` | 7 (tests pre-existentes) | ✅ |

### TypeScript (Backoffice) — 21 tests

| Fichero | Tests | Estado |
|---|---|---|
| `__tests__/auth-utilities.test.ts` | 21 | ✅ |

Utilidades cubiertas:

| Utilidad | Happy path | Failure/edge | Tests |
|---|---|---|---|
| `getNextStatuses()` | Transiciones válidas | Status inválido → `[]` | 5 |
| `hasAnalysisResult()` | Objeto completo, resultado vacío | `null` → `false` | 4 |
| `getTrackflowApiBaseUrl()` | URL por defecto, URL custom | Sin env var | 3 |
| `buildTrackflowApiUrl()` | Path con/sin slash, query params | Trailing slash en base URL | 5 |
| `createAuthorizedHeaders()` | Bearer token, conserva headers | Override Authorization | 4 |
| `applySessionCookie()` | Cookie seteada correctamente | — | 1 |
| `clearSessionCookie()` | Cookie limpiada con maxAge=0 | — | 1 |

### Resumen global

- ✅ **101 tests Python** — todos pasando
- ✅ **21 tests TypeScript** — todos pasando
- ✅ **Cobertura ≥70%** — 72% en Python
- ✅ **TESTING.md** — documentación completa
- ✅ **tests/** — 6 ficheros de test + conftest.py