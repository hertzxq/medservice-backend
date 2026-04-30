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
