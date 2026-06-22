# Implementar funcionalidades
Página de candidatura especifica con el id en el URL

## Poder actualizar datos: Estado y etapa
- PATCH: /records/:id
- Controlar para actualizar: estado y etapa

## Impl Notas dentro de candidatura
- Obtener notas, GET: /records/:id/notes - RESPUESTA EJ:
    ```json
    {
  "data": [
    {
      "id": "cda32176-dfb3-4076-aedc-21448c81a7c5",
      "record_id": "7a791c89-35ae-4ec1-8ffa-ff82223f4a9a",
      "content": "Perfil junior pero con proyectos personales relevantes. Vale la pena considerar.",
      "created_at": "2026-03-24T20:04:32.114Z"
    }
  ],
  "meta": {
    "total": 1
  }
}
    ```
- Añadir notas:, POST: /records/:id/notes - RESPUESTA EJ:
    ```json
    {
    "content": "Texto de la nota"
    }
    ```
    
- Eliminar notas:, DELETE: /records/:id/notes/:note_id



## Mejora diseño general
- Mejora diseño y display de cuando das clic para ver candidatura
- Display bonito con datos distribuidos y bien estructurados (+responsive)