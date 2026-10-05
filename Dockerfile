FROM python:3.12-slim

# The installer requires curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar uv
RUN pip install uv

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app

# Copiar dependencias y lockfile
COPY pyproject.toml uv.lock ./

# Copiar el codigo fuente
COPY . .

# Instalar dependencias
RUN uv sync --no-dev

# Ensure appuser owns everything including .venv
RUN chown -R appuser:appuser /app

# Change to non-root user
USER appuser

# Healthcheck against /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 
  CMD curl -f http://localhost:8000/health || exit 1

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicacion
CMD ["uv", "run", "--no-sync", "uvicorn", "src.pdf_persistence.main:app", "--host", "0.0.0.0", "--port", "8000"]
