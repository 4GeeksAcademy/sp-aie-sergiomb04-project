# ⚛️ Talent Pipeline Tracker

Frontend interno desarrollado con **Next.js + TypeScript** para gestionar el pipeline de candidaturas de una empresa.

El objetivo de esta aplicación es permitir al equipo de People & Talent visualizar, filtrar y administrar candidatos de forma rápida utilizando una API REST ya existente.

---

# 🚀 Stack Tecnológico

- Next.js (App Router)
- React
- TypeScript
- TailwindCSS
- ESLint

---

# 📦 Instalación

## 1. Crear el proyecto

```bash
cd uis/talent-pipeline-tracker
npx create-next-app@latest . --typescript --app --tailwind --eslint
```

---

## 2. Variables de entorno

Crear el archivo `.env.local`:

```env
NEXT_PUBLIC_API_URL=https://playground.4geeks.com/tracker/api/v1
```

---

## 3. Instalar dependencias

```bash
npm install
```

---

## 4. Ejecutar el proyecto

```bash
npm run dev
```

---

# 📁 Estructura del Proyecto

```txt
src/
 ├── app/
 │   ├── page.tsx
 │   ├── candidates/
 │   │   └── [id]/page.tsx
 │   └── components/
 │
 ├── components/
 ├── hooks/
 ├── lib/
 ├── services/
 ├── types/
 └── styles/
```

---

# ✅ Funcionalidades

## 📋 Listado de candidaturas

- Mostrar todos los candidatos.
- Mostrar:
  - Nombre completo
  - Puesto
  - Estado actual
  - Etapa actual
- Buscar por nombre o email.
- Filtrar por estado.
- Filtrar por etapa.
- Navegación sin recarga de página.
- Estados visuales:
  - Loading
  - Success
  - Error

---

## 👤 Detalle del candidato

Mostrar información completa:

- Nombre
- Email
- Teléfono
- Puesto
- LinkedIn
- CV
- Años de experiencia
- Estado
- Etapa
- Fecha de aplicación

Además:

- Actualizar estado (`PATCH /records/:id`)
- Actualizar etapa (`PATCH /records/:id`)
- Ver notas
- Añadir notas
- Eliminar notas

---

## 📝 Gestión de candidaturas

### Crear candidatura

Formulario para registrar nuevos candidatos usando:

```http
POST /records
```

### Editar candidatura

Formulario para editar candidatos existentes usando:

```http
PUT /records/:id
```

---

# 🔄 Manejo Asíncrono

Todas las llamadas a la API utilizan:

```ts
async/await
```

Cada operación implementa:

- Estado de carga
- Estado de éxito
- Estado de error

La interfaz se actualiza dinámicamente sin recargar la página.

---

# 🧠 Tipado

El proyecto utiliza TypeScript para definir:

- Candidate
- Note
- API Responses
- Forms
- Filters

Ejemplo:

```ts
export interface Candidate {
  id: number;
  name: string;
  email: string;
  phone: string;
  position: string;
  status: string;
  stage: string;
}
```

---

# 🌐 API

Documentación oficial:

https://playground.4geeks.com/tracker/api/v1/docs

Endpoints principales:

```http
GET    /records
GET    /records/:id
POST   /records
PUT    /records/:id
PATCH  /records/:id

GET    /records/:id/notes
POST   /records/:id/notes
DELETE /records/:id/notes/:note_id
```

---

# 🎯 Objetivos del Proyecto

- Practicar Next.js App Router
- Manejar estado local con React Hooks
- Consumir APIs REST
- Implementar filtros y búsqueda dinámica
- Gestionar formularios en TypeScript
- Trabajar con UI asíncrona
- Organizar aplicaciones escalables

---

# 📌 Requisitos Importantes

- No usar Redux, Zustand o librerías externas de estado.
- Usar únicamente React Hooks.
- Navegación con App Router.
- Mantener separación clara entre lógica, tipos y componentes.
- Adaptar textos y dominio según el contexto de empresa asignado.

