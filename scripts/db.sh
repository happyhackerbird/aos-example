#!/bin/sh
# Disposable PostgreSQL for this checkout.
#   scripts/db.sh up     start it (idempotent) and print DATABASE_URL
#   scripts/db.sh url    print DATABASE_URL of the running instance
#   scripts/db.sh reset  recreate it from scratch and print DATABASE_URL
#   scripts/db.sh down   remove it, including its data
# The Compose project name isolates instances; AOS sets COMPOSE_PROJECT_NAME per run.
set -eu
cd "$(dirname "$0")/.."
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-aos-example-$(id -un)}"

url() {
  port=$(docker compose port db 5432 2>/dev/null | sed 's/.*://')
  if [ -z "$port" ]; then
    echo "db is not running; run scripts/db.sh up" >&2
    exit 1
  fi
  echo "postgresql://notes:notes@127.0.0.1:$port/notes"
}

case "${1:-}" in
  up)    docker compose up -d --wait db >&2; url ;;
  url)   url ;;
  reset) docker compose down -v --remove-orphans >/dev/null 2>&1 || true
         docker compose up -d --wait db >&2; url ;;
  down)  docker compose down -v --remove-orphans ;;
  *)     echo "usage: scripts/db.sh up|url|reset|down" >&2; exit 2 ;;
esac
