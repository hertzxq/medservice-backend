FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/medservice-backend:/app/medservice_parsers

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

RUN useradd -m -u 1000 appuser

WORKDIR /app/medservice-backend

COPY medservice-backend/pyproject.toml medservice-backend/poetry.lock medservice-backend/README.md ./
RUN poetry lock --no-update --no-interaction --no-ansi \
 && poetry install --only main --no-interaction --no-ansi --no-root

WORKDIR /app
COPY medservice_parsers/ ./medservice_parsers/
COPY medservice-backend/ ./medservice-backend/

WORKDIR /app/medservice-backend
RUN chmod +x entrypoint.sh && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
