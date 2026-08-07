# Auditoria de rendimiento frontend

## Alcance
- Frontend 1: `uis/backoffice`
- Frontend 2: `uis/website`
- Ciclo aplicado: Medir -> Analizar -> Corregir -> Volver a medir

## Medicion inicial (baseline)
Fuente de baseline:
- `docs/audit/before/lighthouse-backoffice-before.json`
- `docs/audit/before/lighthouse-website-before.json`

### Backoffice - baseline
- Performance: 95
- Accessibility: 100
- Best Practices: 100
- SEO: 60
- FCP: 1.2 s
- LCP: 1.5 s
- Speed Index: 1.6 s
- Interactive: 5.4 s
- TBT: 240 ms
- CLS: 0

### Website - baseline
- Performance: 65
- Accessibility: 95
- Best Practices: 100
- SEO: 54
- FCP: 2.2 s
- LCP: 5.4 s
- Speed Index: 10.0 s
- Interactive: 5.5 s
- TBT: 210 ms
- CLS: 0

## Problemas detectados y causa raiz

### 1) JS no usado y costo alto de main thread
Donde aparece:
- Ambos reportes baseline (`unused-javascript`, `mainthread-work-breakdown`, `interactive`).

Causa raiz:
- El baseline venia de un entorno de desarrollo con chunks de devtools de Next en el payload.
- En website, la barra de navegacion era Client Component global por `usePathname`, forzando hidratacion innecesaria en todas las paginas.

### 2) LCP y Speed Index pobres en website
Donde aparece:
- `lighthouse-website-before.json`: LCP 5.4 s, Speed Index 10.0 s.

Causa raiz:
- Demasiado trabajo inicial de JS/estilos para una landing relativamente simple.
- Carga global de fuente mono no usada.

### 3) Duplicacion de codigo de navegacion en backoffice
Donde aparece:
- `uis/backoffice/app/(protected)/layout.tsx`

Por que es duplicado:
- Se renderizaban los mismos enlaces en dos bloques casi identicos (desktop y mobile).

Abstraccion propuesta:
- Extraer un componente compartido para links de navegacion protegida con variante `mobile`.

### 4) Duplicacion de patrones de formularios auth
Donde aparece:
- `uis/backoffice/app/features/auth/components/LoginForm.tsx`
- `uis/backoffice/app/features/auth/components/RegisterForm.tsx`
- `uis/backoffice/app/features/auth/components/ForgotPasswordForm.tsx`
- `uis/backoffice/app/features/auth/components/ResetPasswordForm.tsx`

Por que es duplicado:
- Repeticion de bloques label + input + clases y patron de estado/error.

Abstraccion propuesta:
- Crear un componente `AuthField` (label, input, error) y un hook `useAsyncFormStatus` para gestionar `isSubmitting`, `error`, `success`.

### 5) Links de navegacion no prioritarios precargados
Donde aparece:
- Navbar website y nav protegido backoffice.

Por que es problema:
- Prefetch puede adelantar carga de rutas no criticas y aumentar trabajo en background.

Abstraccion/correccion propuesta:
- Desactivar prefetch en enlaces de navegacion secundarios (`prefetch={false}`).

## Casos de codigo duplicado encontrados

1. Navegacion protegida duplicada (desktop/mobile)
- Ubicacion: `uis/backoffice/app/(protected)/layout.tsx`
- Accion: extraido `ProtectedNavLinks`.

2. Patron de inputs auth repetido
- Ubicacion: formularios auth de backoffice.
- Accion recomendada: `AuthField` compartido.

3. Patron de tarjetas KPI/resumen repetido
- Ubicacion:
  - `uis/website/componentes/Features.tsx`
  - `uis/backoffice/app/(protected)/page.tsx`
- Accion recomendada: componente visual comun de tarjeta (`InfoCard`) por frontend.

## Skills/agentes de rendimiento
- No fue necesario instalar skills adicionales (`core-web-vitals`, `performance`, `web-perf`).
- Se uso Lighthouse en Docker para re-medicion reproducible dentro del dev container.
