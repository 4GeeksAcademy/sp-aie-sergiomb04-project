# Objetivo

Completa íntegramente el Hito 5 del backoffice implementando una interfaz de gestión de inventario en la aplicación Next.js existente, consumiendo la API `/inventory` y respetando todas las reglas de negocio, autenticación y criterios de aceptación.

## Requisitos obligatorios

- Lee `./00-CONTEXT-company.md` antes de crear componentes y utiliza exactamente las entidades, nombres de campos, etiquetas y vocabulario definidos allí.
- Trabaja sobre `uis/backoffice`, no crees una aplicación nueva.
- Toda la información debe consumirse desde la API del backend; no uses datos simulados.

## Configuración

- Configura `NEXT_PUBLIC_INVENTORY_API_URL` en `.env.local`.
- Asegúrate de que el backend esté en ejecución durante el desarrollo.
- Mantén `.env.local` fuera del repositorio mediante `.gitignore`.

## Capa de integración con la API

Crea un módulo centralizado (por ejemplo `lib/inventory.ts`) que contenga todas las llamadas a `/inventory`.

Requisitos:

- Ningún componente debe llamar a `fetch` directamente.
- Todas las peticiones protegidas deben incluir `Authorization: Bearer <token>`.
- Obtén el token desde el sistema de autenticación existente.
- Si la API responde con un error (`4xx` o `5xx`), extrae el mensaje y muéstralo al usuario. Nunca ocultes errores ni los dejes únicamente en la consola.

## Página de productos

Implementa:

`/backoffice/inventory/products`

Debe:

- Obtener los productos desde `GET /inventory/products`.
- Mostrar todos los campos definidos en el CONTEXT junto con `current_stock`.
- Mostrar indicadores visuales del nivel de stock (color, iconos, etc.).
- Documentar mediante un comentario los umbrales utilizados para distinguir stock bajo y stock normal.
- Incluir acciones para registrar una orden de entrada o salida del producto.

## Formulario de órdenes de entrada

Implementa:

`/backoffice/inventory/orders/inbound`

Debe:

- Enviar datos a `POST /inventory/orders/inbound`.
- Permitir seleccionar productos por nombre, nunca por ID manual.
- Limpiar el formulario tras un envío correcto.
- Mostrar un mensaje de confirmación cuando la operación sea exitosa.
- Mostrar los mensajes de error devueltos por la API cuando existan.
- Estar protegido mediante autenticación.

## Formulario de órdenes de salida

Implementa:

`/backoffice/inventory/orders/outbound`

Debe:

- Enviar datos a `POST /inventory/orders/outbound`.
- Al seleccionar un producto obtener y mostrar su `current_stock`.
- Actualizar el stock mostrado automáticamente cuando cambie el producto.
- Avisar en el cliente cuando la cantidad introducida supere el stock disponible antes de enviar el formulario.
- Mostrar el mensaje devuelto por la API cuando responda con HTTP 400 por falta de stock.
- Estar protegido mediante autenticación.

## Historial de órdenes

Implementa:

`/backoffice/inventory/orders`

Debe:

- Obtener los datos desde `GET /inventory/orders`.
- Mostrar para cada registro:
  - Nombre del producto.
  - Cantidad.
  - Tipo de orden (entrada o salida).
  - Fecha de creación.
  - `user_uuid`.
- Diferenciar visualmente las órdenes de entrada y salida.
- Ser una vista únicamente de lectura.

## Protección de rutas

Las siguientes páginas deben requerir autenticación y redirigir al login cuando el usuario no haya iniciado sesión:

- `/backoffice/inventory/products`
- `/backoffice/inventory/orders/inbound`
- `/backoffice/inventory/orders/outbound`
- `/backoffice/inventory/orders`

Utiliza el mismo mecanismo de autenticación ya existente en el proyecto.

## Verificación final

Comprueba que:

- Existe un único módulo para todas las llamadas a la API.
- Ningún componente realiza llamadas `fetch` directamente.
- Todas las peticiones protegidas incluyen el token de autenticación.
- La página de productos muestra datos reales y `current_stock`.
- Los indicadores visuales de stock funcionan correctamente.
- El formulario de entrada muestra confirmaciones y errores legibles.
- El formulario de salida muestra el stock disponible de forma reactiva.
- Existe una advertencia previa cuando la cantidad supera el stock disponible.
- Los errores HTTP 400 del backend se muestran claramente al usuario.
- El historial muestra todas las órdenes con producto, cantidad, tipo, fecha y `user_uuid`.
- Todas las rutas están protegidas.
- Los nombres de entidades, campos y etiquetas coinciden exactamente con `CONTEXT-company.md`.
