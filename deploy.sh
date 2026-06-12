#!/usr/bin/env bash
#
# Deploy script for medservice-backend.
# Запускается на сервере 2 из /opt/medservice/medservice-backend/.
# Подтягивает свежий код бэка и парсеров, пересобирает и перезапускает контейнеры.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARSERS_DIR="${PARENT_DIR}/medservice_parsers"

cd "${SCRIPT_DIR}"

# Refuse to deploy with a dev/placeholder .env. The app's own config guard also
# fails fast on a placeholder SECRET_KEY when ENVIRONMENT=production, but a .env
# left at ENVIRONMENT=development would bypass that — catch it here.
if [[ ! -f .env ]]; then
    echo "[deploy] ERROR: .env not found. Copy .env.production.example to .env and fill it in." >&2
    exit 1
fi
if grep -qE '^ENVIRONMENT=development' .env; then
    echo "[deploy] ERROR: .env has ENVIRONMENT=development — set ENVIRONMENT=production for prod." >&2
    exit 1
fi
if grep -qiE '^SECRET_KEY=.*(REPLACE|CHANGE|example)' .env; then
    echo "[deploy] ERROR: SECRET_KEY in .env is still a placeholder (openssl rand -hex 32)." >&2
    exit 1
fi
# Caddy на этом сервере терминирует TLS для API — домен и ACME-почта обязательны.
if ! grep -qE '^API_DOMAIN=[^[:space:]]+' .env || grep -qE '^API_DOMAIN=.*example\.com' .env; then
    echo "[deploy] ERROR: API_DOMAIN in .env is missing or still example.com." >&2
    exit 1
fi
if ! grep -qE '^ACME_EMAIL=[^[:space:]]+' .env || grep -qE '^ACME_EMAIL=.*example\.com' .env; then
    echo "[deploy] ERROR: ACME_EMAIL in .env is missing or still example.com." >&2
    exit 1
fi

if [[ -d "${PARSERS_DIR}/.git" ]]; then
    echo "[deploy] pulling medservice_parsers"
    git -C "${PARSERS_DIR}" pull --ff-only
else
    echo "[deploy] WARN: ${PARSERS_DIR} is not a git repo, skipping"
fi

echo "[deploy] pulling medservice-backend"
git pull --ff-only

echo "[deploy] building and restarting containers"
docker compose -f docker-compose.prod.yml up -d --build

echo "[deploy] pruning old images"
docker image prune -f

echo "[deploy] done"
docker compose -f docker-compose.prod.yml ps
