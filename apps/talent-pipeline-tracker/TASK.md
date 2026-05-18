# Implementar funcionalidades

## Crear filtros por estado y etapa
### Parámetros

| Nombre | Tipo | Ubicación | Descripción |
|---|---|---|---|
| `status` | `string` | `query` | Filtra por estado del candidato. Valores permitidos: `received`, `in_progress`, `selected`, `discarded`. |
| `stage` | `string` | `query` | Filtra por etapa del proceso. Valores permitidos: `pending`, `review`, `personal_interview`, `technical_interview`, `offer_presented`. |
| `search` | `string` | `query` | Busca coincidencias en `full_name` o `email`. |
| `page` | `integer` | `query` | Número de página para la paginación. Valor mínimo: `1`. Valor por defecto: `1`. |
| `limit` | `integer` | `query` | Cantidad de resultados por página. Mínimo: `1`, máximo: `100`. Valor por defecto: `20`. |