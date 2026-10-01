FROM python:3.12-slim

WORKDIR /app

# Instalar uv
RUN pip install uv

# Copiar dependencias y lockfile
COPY pyproject.toml uv.lock ./

# Instalar dependencias
RUN uv sync --no-dev

# Copiar el codigo fuente
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicacion
CMD ["uv", "run", "uvicorn", "src.pdf_persistence.main:app", "--host", "0.0.0.0", "--port", "8000"]
