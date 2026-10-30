# Imagen de la API. Se construye en dos etapas: la primera instala las dependencias con uv
# (las mismas versiones de uv.lock); la segunda solo copia el entorno listo.
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Primero solo las dependencias: si el código cambia, esta capa se reusa.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra postgres --no-install-project

COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --extra postgres --no-editable


FROM python:3.13-slim
RUN useradd --create-home --uid 1000 tempo
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER tempo
WORKDIR /home/tempo
EXPOSE 8000
# Al arrancar, la API migra la base y, si está vacía, la llena con datos ficticios.
CMD ["uvicorn", "tempo_ledger.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
