## Objetivo

Agregar un sistema de autenticación que:

- Gestione usuarios y perfiles en TinyDB.
- Permita iniciar sesión con JWT.
- Proteja todas las rutas sensibles mediante una dependencia reutilizable (`get_current_user`).

## Requisitos principales

### 1. Usuarios (/users)

- Crear modelo `User` en TinyDB con:
  - `id`
  - `email`
  - `hashed_password`
  - `is_active`
  - `role` (`admin`, `manager` o `user`)
  - `created_at`
- Nunca almacenar nombre, teléfono o dirección en `User`.
- CRUD completo:
  - `POST /users` (registro, contraseña hasheada y creación automática del `Profile`)
  - `GET /users`
  - `GET /users/{id}`
  - `PUT /users/{id}` (solo el usuario o un admin; solo un admin puede cambiar el rol)
  - `DELETE /users/{id}` (elimina también el perfil)
- Los nuevos usuarios tienen rol `user` por defecto.

### 2. Perfiles (/profiles)

Modelo `Profile` en TinyDB con:
- `id`
- `user_id`
- `name`
- `phone`
- `address`

Endpoints:
- `GET /profiles/me`
- `PUT /profiles/me` (solo el propietario puede editarlo).

### 3. Autenticación (/auth)

- `POST /auth/login`
  - Recibe email y contraseña.
  - Valida credenciales.
  - Devuelve un JWT firmado.
- `GET /auth/me`
  - Devuelve email, rol y el perfil asociado.

### 4. JWT

Implementar `get_current_user` que:
- Lea `Authorization: Bearer <token>`.
- Valide y decodifique el JWT.
- Obtenga el usuario desde TinyDB.
- Devuelva `401` si el token es inválido o expiró.

Configurar mediante variables de entorno:
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Usar:
- `OAuth2PasswordBearer`
- `python-jose`
- `passlib` con `bcrypt`

## Protección de rutas

Aplicar `get_current_user` a:
- Todos los endpoints de `/users` excepto `POST /users`.
- `/auth/me`.
- Al menos 5 rutas existentes del proyecto fuera de `/users` y `/auth`.

Respuestas esperadas:
- `401 Unauthorized`: sin token o token inválido.
- `403 Forbidden`: cuando un usuario intenta acceder o modificar recursos que no le pertenecen.

## Verificación

Comprobar en `/docs`:
1. Registrar usuario.
2. Iniciar sesión.
3. Obtener el JWT.
4. Acceder a una ruta protegida con el token.
5. Verificar que:
   - Sin token → `401`.
   - Token inválido o expirado → `401`.

## Restricciones importantes

- Trabajar sobre una rama nueva (`feature/auth`).
- Instalar dependencias con `uv`, no con `pip`.
- `User` y `Profile` solo en TinyDB (nada de Supabase/PostgreSQL).
- Otros módulos solo referencian el `id` de TinyDB (`user_id`).
- No usar autenticación por sesiones ni cookies.
- Nunca guardar contraseñas en texto plano; siempre hashearlas con `bcrypt`.

## Evaluación

Se verificará que:
- El CRUD de usuarios funcione.
- Cada usuario tenga un perfil asociado.
- Los roles estén restringidos (`admin`, `manager`, `user`).
- Las contraseñas estén correctamente hasheadas.
- El login genere un JWT válido.
- `get_current_user` funcione correctamente.
- Las rutas protegidas respondan con `401` cuando corresponda.
- La clave secreta y expiración provengan de variables de entorno.
- Existan al menos 5 rutas adicionales protegidas.
- No haya regresiones en las rutas existentes autenticadas.