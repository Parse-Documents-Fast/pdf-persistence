# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

# Instalar uv desde la imagen oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Configuracion de uv para build reproducible en contenedor
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 1. Copiar manifiestos de dependencias primero para aprovechar cache de Docker
COPY pyproject.toml uv.lock README.md ./

# 2. Instalar solo las dependencias externas (sin el proyecto)
RUN uv sync --frozen --no-dev --no-install-project

# 3. Copiar el codigo fuente e instalar el proyecto
COPY src/ src/
COPY dev/ dev/
RUN uv sync --frozen --no-dev --no-editable

# Etapa final de ejecucion
FROM python:3.12-slim AS runner

# Crear usuario sin privilegios
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Copiar el virtualenv y fuentes con ownership de appuser
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src
COPY --from=builder --chown=appuser:appuser /app/dev /app/dev

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:/app" \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

# Healthcheck nativo con Python (no requiere curl en imagen final)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"]

# Iniciar la aplicacion directamente con uvicorn del virtualenv
CMD ["uvicorn", "pdf_persistence.main:app", "--host", "0.0.0.0", "--port", "8000"]
