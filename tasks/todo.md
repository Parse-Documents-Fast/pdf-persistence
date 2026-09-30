# TODO: pdf-persistence

## Milestone 1 — Foundation

## Task 1: Bootstrap del proyecto + Config
**Description:** Inicializar proyecto con `uv`, configurar dependencias y variables de entorno.
**Acceptance criteria:**
- [ ] `pyproject.toml` con dependencias: `fastapi`, `uvicorn`, `pydantic`, `motor`, `structlog` (dev: `pytest`, `ruff`).
- [ ] `dev/config.py` leyendo `HTTP_ADDR`, `MONGO_URI`, `MONGO_DB_NAME`.

## Task 2: DTOs y RFC 9457
**Description:** Crear modelos y excepciones de dominio.
**Acceptance criteria:**
- [ ] Modelos Request/Response (`DocumentCreate`, `DocumentResponse`).
- [ ] Función para emitir RFC 9457.

## Task 3: Conexión a MongoDB (Motor)
**Description:** Wrapper de conexión asíncrona a la DB y creación de índices.
**Acceptance criteria:**
- [ ] Cliente `Motor` inicializado en el ciclo de vida de la app de FastAPI.
- [ ] Índice único/indexado estándar sobre el campo `checksum`.

---

## Milestone 2 — Repositorio (Core)

## Task 4: Repositorio - Create y GetById
**Description:** Abstracción de base de datos sin HTTP.
**Acceptance criteria:**
- [ ] `core/repository.py`: Funciones `create_document(doc)` y `get_document_by_id(id)`.

## Task 5: Repositorio - Búsqueda por Checksum
**Description:** Soporte para la detección de duplicados.
**Acceptance criteria:**
- [ ] `core/repository.py`: Función `get_document_by_checksum(checksum)`.

## Task 6: Repositorio - List y Delete
**Description:** Operaciones faltantes del CRUD.
**Acceptance criteria:**
- [ ] `list_documents(skip, limit)` y `delete_document(id)`.

---

## Milestone 3 — API HTTP

## Task 7: Rutas principales (Create, GetById)
**Description:** Exponer endpoints HTTP.
**Acceptance criteria:**
- [ ] `POST /documents` devolviendo 201.
- [ ] `GET /documents/{id}` devolviendo 200 o 404 (RFC 9457).

## Task 8: Rutas secundarias y Duplicados
**Description:** Exponer rutas de listado, borrado y validación.
**Acceptance criteria:**
- [ ] `GET /documents/checksum/{checksum}`.
- [ ] `DELETE /documents/{id}` y `GET /documents`.

## Task 9: Deploy y Healthcheck
**Description:** Preparar para producción y Docker.
**Acceptance criteria:**
- [ ] `GET /health` que verifique la conectividad con Mongo (`db.command("ping")`).
- [ ] `Dockerfile` y `docker-compose.yml` (conectado a `fast_pdf_network`).
