#!/usr/bin/env sh
set -eu

BRANCH="${1:-main}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8100/health}"
HEALTH_RETRIES="${HEALTH_RETRIES:-20}"
HEALTH_DELAY_SECONDS="${HEALTH_DELAY_SECONDS:-3}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

command -v git >/dev/null 2>&1 || { echo "git not found in PATH"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker not found in PATH"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl not found in PATH"; exit 1; }

echo "Updating repository..."
git fetch --all --prune
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "Starting containers..."
docker compose up -d --build

echo "Waiting for health endpoint: $HEALTH_URL"
i=1
while [ "$i" -le "$HEALTH_RETRIES" ]; do
  if curl -fsS "$HEALTH_URL" >/dev/null; then
    echo "Healthy (attempt $i/$HEALTH_RETRIES)."
    echo "Deploy successful."
    exit 0
  fi
  i=$((i + 1))
  sleep "$HEALTH_DELAY_SECONDS"
done

echo "Health check failed. Last container status:"
docker compose ps
exit 1
