# PDF Persistence Service

Microservicio interno encargado de interactuar con la base de datos MongoDB para almacenar y gestionar los metadatos y el estado de los documentos del sistema.

## Arquitectura

El proyecto está diseñado bajo un enfoque modular, asíncrono y sin estado (stateless) con FastAPI y Motor:
- `src/pdf_persistence/`: Contiene la lógica del microservicio.
  - `models.py`: DTOs de Pydantic alineados al contrato interno (JSON).
  - `rfc9457.py`: Manejo y serialización estándar de errores en APIs REST (Problem Details).
  - `db.py`: Wrapper asíncrono para MongoDB (Motor), inicialización del pool e índice único.
  - `repository.py`: Abstracción de acceso a datos para interactuar con MongoDB e integración best-effort con Redis.
  - `services.py`: Orquestación y lógica de negocio.
  - `api.py`: Capa de transporte y enrutamiento REST (FastAPI).

### Gestión de MongoDB y Escalabilidad (ADR-0006)
Siguiendo el **ADR-0006** (`pdf-infra gestiona la instancia de MongoDB; pdf-persistence la consume`):
- `pdf-persistence` es completamente sin estado (stateless). Cualquier número de réplicas puede levantarse apuntando a la misma instancia central de MongoDB gestionada por `pdf-infra`.
- La ubicación de la base se inyecta mediante la variable de entorno obligatoria `MONGO_URL` (factor IV de 12-factor: servicios de apoyo como recursos adjuntos).
- Para evitar fragmentación y duplicación de datos entre réplicas, la persistencia inicializa de manera idempotente un **índice único sobre el campo `checksum`** (`idx_unique_checksum`). Si dos réplicas intentan insertar el mismo PDF en paralelo, la base rechaza el duplicado garantizando consistencia (HTTP 409 Conflict).
- La caché en Redis opera bajo el patrón cache-aside de forma no bloqueante (best-effort): si la caché no está disponible, el servicio continúa persistiendo directamente en MongoDB sin interrumpir el flujo.

## Variables de Entorno

| Variable | Descripción | Default / Requerido |
|---|---|---|
| `MONGO_URL` | URL de conexión a MongoDB (incluye credenciales si aplica) | **Obligatoria** (sin default en código) |
| `MONGO_DB_NAME` | Nombre de la base de datos en MongoDB | `pdf_persistence` |
| `HTTP_ADDR` | Dirección de escucha del servidor HTTP | `0.0.0.0:8000` |
| `REDIS_HOST` | Host de la instancia Redis para caché de checksums | `redis-cache` |
| `REDIS_PORT` | Puerto de la instancia Redis | `6379` |
| `REDIS_TTL` | Tiempo de vida de claves de checksum en Redis (segundos) | `604800` (7 días) |

## Configuración y Ejecución

El proyecto utiliza `uv` como gestor de paquetes de Python en espacio de usuario.

```bash
# Sincronizar el entorno y dependencias
uv sync

# Ejecutar tests
uv run pytest

# Chequear y corregir linter/formateo (Ruff)
uv run ruff check .
uv run ruff format .
```

## Endpoints Principales

- `POST /documents`: Crea un nuevo registro en estado `pending` o `done`. Recibe JSON (`PersistCreateRequest`). Si el checksum ya existe, devuelve `409 Conflict`.
- `GET /documents/by-checksum?checksum={checksum}`: Consulta rápidamente por un documento usando su hash.
- `GET /documents`: Listado paginado de documentos extraídos (`skip`, `limit`).
- `GET /documents/{id}`: Obtención del documento procesado (ID, contenido Markdown, metadata, estado).
- `PATCH /documents/{id}`: Actualiza el estado y contenido del documento de forma asíncrona.
- `DELETE /documents/{id}`: Eliminación de un registro y desalojo de caché.
- `GET /health`: Comprobación de salud y conectividad viva con MongoDB (`ping`).

## Prevención de Duplicados
Todo documento es contrastado utilizando su hash criptográfico SHA-256 mediante el índice único a nivel base de datos y la clave `dedupe:checksum:{checksum}` en Redis.
