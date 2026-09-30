# Spec: pdf-persistence

**Estado:** Propuesto

## Objective

`pdf-persistence` es el servicio encargado de la **persistencia en base de datos** del sistema *Parse Documents Fast*. Su única responsabilidad es almacenar y recuperar documentos en formato Markdown y su metadata asociada (incluyendo el checksum para detectar duplicados) en MongoDB. 

Es un servicio de almacenamiento pasivo: no realiza transformaciones, no extrae texto y no valida formatos. Es la fuente de verdad del estado de los documentos.

**Usuario:** Únicamente `pdf-main`, vía HTTP síncrono (ADR-0004).

**Éxito:** Guardar, recuperar, listar, borrar y buscar documentos por checksum correctamente en MongoDB con tiempos de respuesta óptimos.

---

## Alcance (qué hace y qué NO hace)

### Hace
1. Proveer un CRUD básico (Create, Read, List, Delete) para documentos.
2. Almacenar contenido **exclusivamente en Markdown** (ADR-0005).
3. Proveer un endpoint para búsqueda por `checksum` para la detección de duplicados (lógica portada del monolito).
4. Interactuar directamente con MongoDB.

### No hace
- **No** guarda archivos binarios (ni PDF, ni imágenes).
- **No** convierte entre formatos (ni de HTML a Markdown, ni viceversa).
- **No** se comunica mediante colas de mensajes (Redis Streams); su modelo es estrictamente HTTP síncrono.
- **No** recibe tráfico público (sin Traefik labels) ni es llamado por otros servicios que no sean `pdf-main`.

---

## Tech Stack

| Componente | Elección | Justificación |
|---|---|---|
| Lenguaje | Python 3.12+ | Continuidad con el monolito y el stack de `pdf-validator`. |
| Framework | FastAPI | Mismo framework del monolito y validator; manejo natural de RFC 9457. |
| Base de Datos | MongoDB (Motor - async) | Driver asíncrono para no bloquear el event loop de FastAPI en las operaciones de I/O. |
| Validaciones / DTOs | Pydantic v2 | Modelado de datos robusto y estandarizado. |
| Observabilidad | structlog | Logs estructurados en JSON a `stdout` (Twelve-Factor App). |
| Gestor de paquetes | `uv` | Estándar en los repositorios Python del sistema. |
| Testing | `pytest` + `testcontainers` (o mongomock) | Pruebas de integración reales contra una base de datos efímera. |

---

## DTOs (contrato de wire — snake_case, ADR-0002)

**Modelo de Base de Datos / Documento:**
```jsonc
{
  "id": "60d5ecb54... (ObjectId)",
  "content": "# Título\n\nContenido en markdown...",
  "checksum": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",
  "original_format": "pdf", // o "markdown"
  "title": "Documento de ejemplo",
  "created_at": "2024-10-01T12:00:00Z"
}
```

**Errores:** RFC 9457 (ADR-0001) para 404 Not Found, 400 Bad Request y 409 Conflict (duplicado).

---

## Endpoints

| Método | Path | Éxito | Errores (RFC 9457) |
|---|---|---|---|
| `POST` | `/documents` | `201` Documento creado | `400` Payload inválido, `409` Duplicado (si aplica) |
| `GET` | `/documents/{id}` | `200` Documento | `404` No encontrado |
| `GET` | `/documents` | `200` Lista paginada | - |
| `DELETE` | `/documents/{id}` | `204` No Content | `404` No encontrado |
| `GET` | `/documents/checksum/{checksum}` | `200` Documento | `404` No encontrado |
| `GET` | `/health` | `200` `{"status":"ok"}` | `503` Si Mongo no responde |

---

## Configuración (variables de entorno)

| Variable | Default | Descripción |
|---|---|---|
| `HTTP_ADDR` | `:8002` | Puerto interno de escucha (diferente a validator/main). |
| `MONGO_URI` | `mongodb://localhost:27017` | URI de conexión a la base de datos MongoDB. |
| `MONGO_DB_NAME` | `pdf_db` | Nombre de la base de datos a usar. |

---

## Boundaries y Coordinación

- Nivel de red: Solo accesible internamente (`fast_pdf_network`).
- Arquitectura: Capa de persistencia (Motor) separada de la capa HTTP (FastAPI) (siguiendo el espíritu de ADR-0004).
- Coordinación: `pdf-main` es la fuente de verdad del contrato de los endpoints.
