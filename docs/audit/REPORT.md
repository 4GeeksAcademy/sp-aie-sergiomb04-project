# Reporte de optimizaciones frontend

## Correcciones realizadas

### 1) Website: reducir hidratacion global
- Archivo: `uis/website/componentes/Navbar.tsx`
- Cambio:
  - Se elimino `use client` y `usePathname` para volver el navbar Server Component.
  - Se simplifico render de links y se desactivo prefetch en navegacion.

Impacto esperado:
- Menos JS cliente en landing.
- Menos trabajo de hidratacion inicial.

### 2) Website y Backoffice: recorte de fuente no usada
- Archivos:
  - `uis/website/app/layout.tsx`
  - `uis/backoffice/app/layout.tsx`
  - `uis/website/app/globals.css`
  - `uis/backoffice/app/globals.css`
- Cambio:
  - Se elimino `Geist_Mono` y su variable de tema.

Impacto esperado:
- Menos bytes y menos trabajo de estilo/render en carga inicial.

### 3) Backoffice: extraccion de componente reutilizable
- Archivos:
  - `uis/backoffice/app/features/layout/components/ProtectedNavLinks.tsx` (nuevo)
  - `uis/backoffice/app/(protected)/layout.tsx`
- Cambio:
  - Se extrajo la navegacion duplicada desktop/mobile a un componente compartido.
  - Se desactivo prefetch en esos enlaces.

Impacto esperado:
- Menos duplicacion de codigo.
- Menos riesgo de inconsistencias al cambiar rutas.

## Medicion after (post-cambio)
Archivos generados:
- `docs/audit/after/lighthouse-backoffice-after.json`
- `docs/audit/after/lighthouse-website-after.json`

Metodo:
- Lighthouse ejecutado desde contenedor Docker con Chrome incluido (`patrickhulce/lhci-client:0.13.0`) y `--preset=desktop`.

## Comparativa before/after

### Backoffice
- Performance: 95 -> 100
- Accessibility: 100 -> 100
- Best Practices: 100 -> 96
- SEO: 60 -> 100
- FCP: 1.2 s -> 0.3 s
- LCP: 1.5 s -> 0.3 s
- Speed Index: 1.6 s -> 1.0 s
- Interactive: 5.4 s -> 1.2 s
- TBT: 240 ms -> 50 ms
- CLS: 0 -> 0

### Website
- Performance: 65 -> 94
- Accessibility: 95 -> 94
- Best Practices: 100 -> 96
- SEO: 54 -> 100
- FCP: 2.2 s -> 0.4 s
- LCP: 5.4 s -> 1.5 s
- Speed Index: 10.0 s -> 1.3 s
- Interactive: 5.5 s -> 1.5 s
- TBT: 210 ms -> 80 ms
- CLS: 0 -> 0

## Impacto por mejora

1. Quitar hidratacion cliente del navbar (website)
- Relacion directa con mejora en FCP/LCP/SI al reducir trabajo inicial de JS.

2. Eliminar fuente mono no usada (ambos)
- Aporta reduccion de carga y simplifica recursos criticos.

3. Extraer `ProtectedNavLinks` (backoffice)
- Mejora mantenibilidad y consistencia.
- Facilita evolucion futura sin duplicar render/logica.

## Conclusiones
- La optimizacion con mayor efecto fue reducir JS/hidratacion global en website.
- El recorte de recursos no usados (fuente mono) mejora la base de rendimiento en ambos frontends.
- La extraccion de componente compartido en backoffice reduce deuda tecnica y el costo de mantenimiento.
- No se reescribio arquitectura: se aplicaron mejoras dirigidas, medibles y con bajo riesgo de regresion.

## Notas de calidad
- `uis/backoffice` tiene errores de lint preexistentes en archivos no tocados en esta tarea (tests y componentes de incidencias).
- `uis/website` presenta problema de permisos en `node_modules` para correr lint/build localmente desde este contenedor, aunque la app sirve correctamente en runtime.
