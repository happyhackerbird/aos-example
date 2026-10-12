#!/bin/sh
# Start, check and stop one notes server for a verification run.
#   app.sh start  RUN_DIR   start `python -m notes` against $DATABASE_URL, wait for /health, print the URL
#   app.sh doctor RUN_DIR   read-only: is the server recorded in RUN_DIR ours, up, healthy, on this database?
#   app.sh stop   RUN_DIR   stop the server recorded in RUN_DIR (idempotent); every other file stays
# RUN_DIR holds server.pid, url, database_url and server.log. Use evidence/<UTC stamp>/ so the
# server log is kept with the rest of the proof.
set -eu
repo=$(cd "$(dirname "$0")/../../../.." && pwd)

usage() { echo "usage: app.sh start|doctor|stop RUN_DIR" >&2; exit 2; }
[ $# -eq 2 ] || usage
cmd=$1
mkdir -p "$2"
run=$(cd "$2" && pwd)

# Succeeds, setting $pid, only if RUN_DIR records a process that is still a notes server.
ours() {
  [ -f "$run/server.pid" ] || return 1
  pid=$(cat "$run/server.pid")
  ps -p "$pid" -o command= 2>/dev/null | grep -q -- '-m notes'
}

case "$cmd" in
  start)
    : "${DATABASE_URL:?DATABASE_URL is not set; run: export DATABASE_URL=\$(scripts/db.sh up)}"
    [ -x "$repo/.venv/bin/python" ] || { echo "no .venv; run: uv sync --frozen" >&2; exit 1; }
    if ours; then echo "already running: pid $pid, $(cat "$run/url")" >&2; exit 1; fi
    printf '%s\n' "$DATABASE_URL" >"$run/database_url"
    (cd "$repo" && .venv/bin/python -m notes --port 0 </dev/null >"$run/url" 2>"$run/server.log" &
     echo $! >"$run/launcher.pid")
    launcher=$(cat "$run/launcher.pid")
    i=0
    while [ $i -lt 100 ]; do
      kill -0 "$launcher" 2>/dev/null || { echo "server exited; see $run/server.log" >&2; tail -5 "$run/server.log" >&2; exit 1; }
      url=$(head -1 "$run/url" 2>/dev/null || true)
      if [ -n "$url" ] && curl -fsS "$url/health" >/dev/null 2>&1; then
        # $! can be a wrapper shell (macOS /bin/sh with `nohup cmd &` does this), so record
        # the process that holds the port, after checking it is the launcher or its child.
        pid=$(lsof -nP -iTCP:"${url##*:}" -sTCP:LISTEN -t | head -1)
        if [ "$pid" != "$launcher" ] && [ "$(ps -p "$pid" -o ppid= | tr -d ' ')" != "$launcher" ]; then
          echo "port ${url##*:} is held by pid $pid, which is not ours (launcher $launcher)" >&2; exit 1
        fi
        echo "$pid" >"$run/server.pid"
        echo "$url"; exit 0
      fi
      sleep 0.2; i=$((i + 1))
    done
    echo "no /health answer within 20s; see $run/server.log (launcher pid $launcher; run app.sh stop)" >&2
    exit 1
    ;;
  doctor)
    fail=0
    check() { if [ "$1" = ok ]; then echo "ok    $2"; else echo "FAIL  $2"; fail=1; fi; }
    if ours; then check ok "process $pid is a notes server started for $run"
    else check bad "no live notes server recorded in $run/server.pid"; fi
    url=$(head -1 "$run/url" 2>/dev/null || true)
    port=${url##*:}
    if [ -n "$url" ] && body=$(curl -fsS "$url/health" 2>/dev/null); then check ok "$url/health -> $body"
    else check bad "${url:-?}/health does not answer 200"; fi
    owner=$(lsof -nP -iTCP:"${port:-0}" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)
    if [ -n "$owner" ] && [ "$owner" = "${pid:-}" ]; then check ok "port $port is held by pid $owner"
    else check bad "port ${port:-?} is held by '${owner:-nobody}', not pid ${pid:-?}"; fi
    # This checkout's database: scripts/db.sh's, or the runner-provided DATABASE_URL when Compose has none.
    source="scripts/db.sh url"
    current=$(cd "$repo" && scripts/db.sh url 2>/dev/null) || { source='$DATABASE_URL (no Compose database)'; current=${DATABASE_URL:-}; }
    if [ -n "$current" ] && [ "$current" = "$(cat "$run/database_url" 2>/dev/null)" ]; then check ok "database matches $source: $current"
    else check bad "server database '$(cat "$run/database_url" 2>/dev/null)' != this checkout's '$current'"; fi
    echo "build $(git -C "$repo" rev-parse --short HEAD)$(git -C "$repo" diff --quiet HEAD -- notes || echo ' + uncommitted changes in notes/')"
    exit $fail
    ;;
  stop)
    # Only PIDs this script recorded: the server, then its launcher if that outlived it.
    stopped=""
    for file in server.pid launcher.pid; do
      [ -f "$run/$file" ] || continue
      p=$(cat "$run/$file")
      if ps -p "$p" -o command= 2>/dev/null | grep -q -e '-m notes' -e '^/bin/sh'; then
        kill -TERM "$p" 2>/dev/null || true
        i=0
        while kill -0 "$p" 2>/dev/null && [ $i -lt 50 ]; do sleep 0.2; i=$((i + 1)); done
        if kill -0 "$p" 2>/dev/null; then kill -KILL "$p"; fi
        stopped="$stopped $p"
      fi
      rm -f "$run/$file"
    done
    echo "stopped pids:${stopped:- none running}; evidence kept in $run"
    ;;
  *) usage ;;
esac
