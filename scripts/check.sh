#!/bin/sh
# The full check: unit tests, then the browser verification, against a fresh database.
# With DATABASE_URL already set (for example provisioned by the runner) that database is
# used and reset; otherwise a disposable one is started with scripts/db.sh and removed
# at the end. Exit status is the first failure's.
set -u
cd "$(dirname "$0")/.."
own_db=0
if [ -z "${DATABASE_URL:-}" ]; then
  url=$(scripts/db.sh reset) || exit 1
  export DATABASE_URL="$url"
  own_db=1
fi
status=0
uv run --frozen pytest -q || status=$?
if [ "$status" -eq 0 ]; then
  uv run --frozen python scripts/verify_browser.py || status=$?
fi
if [ "$own_db" -eq 1 ]; then
  scripts/db.sh down >/dev/null 2>&1
fi
exit "$status"
