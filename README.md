# PDF Persistence Service

Microservicio interno encargado de interactuar con la base de datos MongoDB para almacenar y gestionar los metadatos y el estado de los documentos del sistema.

## Arquitectura

El proyecto está diseñado bajo un enfoque modular y asíncrono con FastAPI y Motor:
- src/pdf_persistence/: Contiene la lógica del microservicio.
  - models.py: DTOs de Pydantic alineados al contrato interno (JSON).
  - fc9457.py: Manejo y serialización estándar de errores en APIs REST (Problem Details).
  - db.py: Wrapper asíncrono para MongoDB (Motor), inicialización de base de datos e índices.
  - epository.py: Abstracción de datos para interactuar con la DB y Redis (Create, List, Get, Delete, Update, FindByChecksum).
  - services.py: Orquestación y lógica de negocio.
  - pi.py: Capa de transporte y enrutamiento REST (FastAPI).

## Dependencias

- **FastAPI / Uvicorn:** Base para el servicio HTTP asíncrono.
- **Motor / PyMongo:** Cliente de MongoDB asíncrono.
- **Pydantic / Pydantic-Settings:** Serialización de datos y manejo de variables de entorno.
- **Redis:** Para cacheo de checksums evitando consultas constantes a la base de datos de los duplicados.

## Configuración y Ejecución

El proyecto utiliza uv como manejador de paquetes de Python en espacio de usuario.

`ash
# Sincronizar el entorno y dependencias
uv sync

# Ejecutar tests
uv run pytest

# Chequear y corregir linter/formateo (Ruff)
uv run ruff check .
uv run ruff format .
`

## Endpoints Principales

- POST /documents: Crea un nuevo registro en estado pending o done. Recibe JSON (PersistCreateRequest).
- GET /documents/by-checksum: Consulta rápidamente por un documento usando su hash.
- GET /documents: Listado paginado de documentos extraídos.
- GET /documents/{id}: Obtención del documento procesado (ID, contenido Markdown, metadata, estado).
- PATCH /documents/{id}: Actualiza el estado y contenido del documento de forma asíncrona.
- DELETE /documents/{id}: Eliminación de un registro.

## Prevención de Duplicados
Todo documento es contrastado utilizando su hash SHA-256. Si existe, se descarta la creación (HTTP 409) y se avisa de la colisión para mantener la base de datos eficiente y limpia.
