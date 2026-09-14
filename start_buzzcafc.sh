#!/usr/bin/env bash
# ===================================================
# Buzzcaf (coffee) - macOS / Linux launcher. The .bat equivalent: one file,
# runs everything. First run does its own setup (Python venv + npm install);
# afterwards it is instant.
#
#   ./start_buzzcafc.sh                  run Ops + Website together
#   ./start_buzzcafc.sh --assistant      also start the assistant watcher
#                                        (mail inbox sorting, daily brief)
#   ./start_buzzcafc.sh --website-only   skip Ops
#   ./start_buzzcafc.sh --ops-only       skip the website
#
# When it finishes: Ctrl+C. Both apps stop together; no leftover processes.
#
# Needs: python3 (3.10+) and Node.js 18+ (npm). On macOS:  brew install python3 node
# ===================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
VENV_PY="$APP_DIR/.venv/bin/python"

ASSISTANT=false
WEBSITE=true
OPS=true
for arg in "$@"; do
  case "$arg" in
    --assistant)    ASSISTANT=true ;;
    --website-only) OPS=false ;;
    --ops-only)     WEBSITE=false ;;
  esac
done

# ── tool checks ────────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "python3 not found. Install it first:  brew install python3" >&2; exit 1; }
if [ "$WEBSITE" = true ]; then
  command -v npm >/dev/null 2>&1 || { echo "Node.js (npm) not found. Install it first:  brew install node" >&2; exit 1; }
fi

# ── first-run setup ────────────────────────────────────────────────────
if [ "$OPS" = true ] && [ ! -x "$VENV_PY" ]; then
  echo "== First run: creating .venv and installing Buzzcaf Ops dependencies =="
  python3 -m venv "$APP_DIR/.venv"
  "$VENV_PY" -m pip install --upgrade pip >/dev/null
  "$VENV_PY" -m pip install -r "$APP_DIR/ops/requirements.txt"
fi

if [ ! -f "$APP_DIR/website/.env" ]; then
  echo "== First run: copying website/.env.example to .env (edit it when ready) =="
  cp "$APP_DIR/website/.env.example" "$APP_DIR/website/.env"
fi
if [ ! -f "$APP_DIR/ops/.env" ]; then
  echo "== First run: copying ops/.env.example to .env (only needed for Mail / Claude) =="
  cp "$APP_DIR/ops/.env.example" "$APP_DIR/ops/.env"
fi

if [ "$WEBSITE" = true ] && [ ! -d "$APP_DIR/website/node_modules" ]; then
  echo "== First run: installing website node modules (npm install, one time) =="
  (cd "$APP_DIR/website" && npm install)
fi

# ── runners ────────────────────────────────────────────────────────────
run_ops() {
  if [ "$ASSISTANT" = true ]; then
    exec "$VENV_PY" -X utf8 "$APP_DIR/ops/run.py" --assistant
  else
    exec "$VENV_PY" -X utf8 "$APP_DIR/ops/run.py"
  fi
}

run_website() {
  cd "$APP_DIR/website"
  # The committed prisma/dev.db already has the schema; dev mode generates the
  # client in postinstall. If your .env points at a fresh database, run
  # `npx prisma migrate dev && npm run seed` once before launching.
  exec npx next dev --port 3000
}

# ── launch (each app backgrounds itself; Ctrl+C kills both) ────────────
echo "==================================================="
if [ "$OPS" = true ];   then echo " Buzzcaf Ops      -> http://127.0.0.1:8010"; fi
if [ "$WEBSITE" = true ]; then echo " Buzzcaf Website  -> http://localhost:3000"; fi
echo " Stop both: Ctrl+C"
echo "==================================================="

trap 'kill $(jobs -p) 2>/dev/null; wait; exit 130' INT TERM

if [ "$OPS" = true ];     then run_ops &     fi
if [ "$WEBSITE" = true ]; then run_website & fi
wait
