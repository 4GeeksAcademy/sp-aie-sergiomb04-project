# Implementar funcionalidades

## Crear página detalle de candidatura
Obtener y mostrar datos (/candidates/[id] -> GET /records/:id)
Por cada elemento de tabla debe redireccionar a los datos del id (Crear Anchor y enviar)

### Ejemplo respuesta
```json
{
  "id": "53f2bbdc-4ea0-4b34-b076-4f8e7c2736ac",
  "full_name": "Michael Smith",
  "email": "michael.smith@gmail.com",
  "phone": "+1 423-828-6619",
  "position": "Jefa/e de Gabinete",
  "linkedin_url": "https://linkedin.com/in/michael-smith",
  "cv_url": "https://storage.example.com/cv/53f2bbdc-4ea0-4b34-b076-4f8e7c2736ac.pdf",
  "status": "in_progress",
  "stage": "review",
  "experience_years": 6,
  "notes_count": 1,
  "applied_at": "2026-02-28T20:04:32.114Z",
  "updated_at": "2026-03-27T20:04:32.114Z"
}```