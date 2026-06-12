#!/usr/bin/env bash
#
# Exposes the mini-app (localhost:5173) over a public HTTPS URL so SMS review
# links open on a real phone, and writes that URL into ../.env (MINI_PUBLIC_URL).
#
# Requires: cloudflared (`brew install cloudflared`). The mini dev server must
# already be running on :5173 and Vite must allow external hosts (it does:
# server.allowedHosts = true in vite.config.ts).
#
# Usage:  ./scripts/start-sms-tunnel.sh
# Stop:   Ctrl-C (then optionally reset MINI_PUBLIC_URL=http://localhost:5173)
set -euo pipefail

ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
LOG="$(mktemp -t medservice-tunnel)"

echo "Starting cloudflared tunnel to http://localhost:5173 ..."
cloudflared tunnel --url http://localhost:5173 >"$LOG" 2>&1 &
TUNNEL_PID=$!
trap 'kill "$TUNNEL_PID" 2>/dev/null || true' EXIT

URL=""
for _ in $(seq 1 30); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$LOG" | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done

if [ -z "$URL" ]; then
  echo "Failed to obtain a tunnel URL. Log:"; cat "$LOG"; exit 1
fi

echo "Tunnel URL: $URL"
# Update MINI_PUBLIC_URL in .env (portable sed -i).
if grep -q '^MINI_PUBLIC_URL=' "$ENV_FILE"; then
  sed -i.bak "s#^MINI_PUBLIC_URL=.*#MINI_PUBLIC_URL=$URL#" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
  printf '\nMINI_PUBLIC_URL=%s\n' "$URL" >> "$ENV_FILE"
fi
echo "Wrote MINI_PUBLIC_URL=$URL to $ENV_FILE"
echo "Restart (or touch app/main.py) the backend so it picks up the new URL."
echo "Tunnel is live. Press Ctrl-C to stop."
wait "$TUNNEL_PID"
