#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] waiting for postgres at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
for i in $(seq 1 30); do
    if python -c "import socket,sys,os; s=socket.socket(); s.settimeout(2); s.connect((os.environ.get('POSTGRES_HOST','postgres'), int(os.environ.get('POSTGRES_PORT','5432')))); s.close()" 2>/dev/null; then
        echo "[entrypoint] postgres is up"
        break
    fi
    echo "[entrypoint] postgres not ready yet ($i/30)"
    sleep 2
done

echo "[entrypoint] running alembic migrations"
alembic upgrade head

echo "[entrypoint] starting gunicorn"
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers "${GUNICORN_WORKERS:-2}" \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 120
