# Implementation Plan: pdf-persistence

## Overview

Construir `pdf-persistence`, el servicio encargado del almacenamiento de Markdown en MongoDB para el sistema *Parse Documents Fast*. Implementado en Python/FastAPI, expone operaciones CRUD por HTTP síncrono para que `pdf-main` gestione el estado y la detección de duplicados por checksum.

## Architecture Decisions

1. **Patrón Repositorio (`core/repository.py`)** — Separación estricta de la lógica de acceso a datos usando un driver asíncrono (`Motor`).
2. **Markdown canónico (ADR-0005)** — Solo se guarda contenido Markdown, la persistencia no realiza ninguna conversión de formato.
3. **Detección de duplicados delegada en BD** — Búsqueda directa por el campo `checksum` (con índice en MongoDB).
4. **RFC 9457 estricto (ADR-0001)** — Para todos los errores HTTP (404, 400, etc.).

## Task List

### Milestone 1 — Foundation y Conexión DB
- [ ] Task 1: Bootstrap del proyecto Python (`uv`), configuración desde env y logger.
- [ ] Task 2: DTOs, modelo Pydantic del Documento y helpers RFC 9457.
- [ ] Task 3: Cliente de MongoDB asíncrono (`Motor`) y script de índices (`checksum`).

### Checkpoint: Foundation
- `uv run pytest` corre y la conexión a una DB de prueba local funciona.

### Milestone 2 — Lógica de Repositorio (Core)
- [ ] Task 4: Implementar Create y Get por ID (lógica Mongo puro, sin HTTP).
- [ ] Task 5: Implementar Get por Checksum (para detección de duplicados).
- [ ] Task 6: Implementar Listado y Delete.

### Checkpoint: Core
- Cobertura alta en `core/repository.py`, pasando pruebas con mock de DB o Testcontainers.

### Milestone 3 — API HTTP y Deploy
- [ ] Task 7: Endpoints `POST /documents` y `GET /documents/{id}` con validaciones.
- [ ] Task 8: Endpoints `GET /documents`, `DELETE`, y `GET /documents/checksum/{checksum}`.
- [ ] Task 9: `GET /health` validando ping a Mongo, `main.py`, y `Dockerfile`/`docker-compose.yml`.

### Checkpoint: Complete
- Servicio desplegable en Docker, interactuando por HTTP y guardando datos reales en MongoDB.
