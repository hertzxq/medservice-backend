FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/app/medservice-backend:/app/medservice_parsers

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# xvfb: виртуальный дисплей для headful-парсинга Google на headless-сервере
# (verify_reviews.py заворачивает google-парс в xvfb-run, если он есть).
# python3-venv: в noble-базе системный python без ensurepip — нужен для venv парсеров.
# Пакет заодно возвращает PEP668-маркер EXTERNALLY-MANAGED, который запрещает
# poetry/pip ставить в системный python — в контейнере он не нужен, удаляем.
RUN apt-get update && apt-get install -y --no-install-recommends xvfb python3-venv \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /usr/lib/python3*/EXTERNALLY-MANAGED

# UID 1000 занят встроенным пользователем ubuntu в noble-базе — берём свободный.
RUN useradd -m -u 10001 appuser

WORKDIR /app/medservice-backend

COPY medservice-backend/pyproject.toml medservice-backend/poetry.lock medservice-backend/README.md ./
RUN poetry lock --no-update --no-interaction --no-ansi \
 && poetry install --only main --no-interaction --no-ansi --no-root

WORKDIR /app
COPY medservice_parsers/ ./medservice_parsers/
# Fail fast if the parsers checkout is missing/misnamed instead of breaking at runtime.
RUN test -d /app/medservice_parsers/yandex_reviews \
 || (echo "ERROR: medservice_parsers/ not found in build context (expected sibling of medservice-backend/)" && exit 1)

# Изолированный venv парсеров — verify_reviews.py запускает их как subprocess
# (medservice_parsers/.venv/bin/python). Свои зависимости + браузеры:
#   chromium — yandex/prodoctorov/napopravku (и google-fallback),
#   chrome   — реальный Google Chrome для headful google (channel="chrome").
RUN python -m venv /app/medservice_parsers/.venv \
 && /app/medservice_parsers/.venv/bin/pip install --no-cache-dir \
      "playwright>=1.49,<1.50" beautifulsoup4 lxml pydantic asyncpg "httpx>=0.28" \
 && /app/medservice_parsers/.venv/bin/playwright install --with-deps chromium chrome \
 && chmod -R a+rx /ms-playwright

COPY medservice-backend/ ./medservice-backend/

WORKDIR /app/medservice-backend
RUN chmod +x entrypoint.sh && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
