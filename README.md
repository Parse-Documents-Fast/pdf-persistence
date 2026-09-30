# PDF Persistence Service

Microservicio encargado de recibir archivos PDF, procesarlos utilizando extracción estructurada con Inteligencia Artificial (`pymupdf4llm`), y almacenarlos en una base de datos MongoDB manteniendo un registro único por documento.

## Arquitectura

El proyecto está diseñado bajo un enfoque de Arquitectura Limpia modularizada:
- `core/`: Expone las interfaces públicas, enrutadores y servicios principales (desacoplamiento total).
- `src/pdf_persistence/`: Contiene la lógica detallada dividida por capas.
  - `models.py`: DTOs de Pydantic.
  - `rfc9457.py`: Manejo y serialización estándar de errores en APIs REST.
  - `db.py`: Wrapper asíncrono para MongoDB (`Motor`) y gestión de índices.
  - `repository.py`: Abstracción de datos (Create, List, Get, Delete).
  - `services.py`: Orquestación, conversión de PDF a Markdown e inspección de duplicados (mediante SHA-256).
  - `api.py`: Capa de transporte y enrutamiento (FastAPI).

## Dependencias

- **FastAPI / Uvicorn:** Base para el servicio HTTP asíncrono.
- **Motor / PyMongo:** Cliente de MongoDB asíncrono.
- **Pydantic / Pydantic-Settings:** Serialización de datos y manejo de variables de entorno.
- **PyMuPDF4LLM:** Extracción de texto desde PDF a formato Markdown limpio para LLMs.
- **Python-Multipart:** Manejo de uploads de archivos (`multipart/form-data`).

## Configuración y Ejecución

El proyecto utiliza `uv` como manejador de paquetes.

```bash
# Sincronizar el entorno y dependencias
uv sync

# Ejecutar tests
uv run python -m pytest

# Chequear linter (Ruff)
uv run ruff check .
```

## Endpoints Principales

- `POST /documents`: Subida de un PDF y su título. Extrae a Markdown y persiste.
- `GET /documents`: Listado paginado de documentos extraídos.
- `GET /documents/{id}`: Obtención del documento procesado (ID, contenido Markdown, metadata).
- `DELETE /documents/{id}`: Eliminación de un registro.

## Casos de Uso Avanzados
- **Prevención de Duplicados**: Todo documento entrante pasa por un chequeo rápido en memoria generándose su hash `SHA-256`. Si existe, se descarta y se devuelve error de conflicto evitando uso excesivo de procesamiento de PDFs.
