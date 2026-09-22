#!/usr/bin/env bash
# Answer Layer — setup and run.
#
#   ./run.sh check              verify everything. costs nothing.
#   ./run.sh smoke              2 prompts x 1 run. pennies. do this first.
#   ./run.sh probe              10 prompts x 3 runs. ~$5-12.
#   ./run.sh full               18 prompts x 3 runs. ~$10-20.
#   ./run.sh surface <url> [..] agent-surface audit. free, no key needed.
#   ./run.sh diff <old> <new>   compare two harvests. free.
#   ./run.sh serve [port]       preview the site at localhost. free.
#
# Paid commands ask before spending.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
PY="$VENV/bin/python"
OUT="$HERE/answer-layer/out/rebuild"
SCRIPTS="$HERE/answer-layer/scripts"
KEYFILE="$HOME/.anthropic-env"

b()  { printf '\033[1m%s\033[0m\n' "$*"; }
ok() { printf '  \033[32mok\033[0m   %s\n' "$*"; }
no() { printf '  \033[31mfail\033[0m %s\n' "$*"; }
hm() { printf '  \033[33m..\033[0m   %s\n' "$*"; }

ensure_venv() {
  if [ ! -x "$PY" ]; then
    hm "no venv — creating one"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
  fi
  if ! "$PY" -c 'import anthropic, pydantic' 2>/dev/null; then
    hm "installing anthropic + pydantic"
    "$VENV/bin/pip" install -q anthropic pydantic
  fi
}

ensure_key() {
  [ -f "$KEYFILE" ] && . "$KEYFILE"
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    no "no API key"
    echo
    echo "  Create one at console.anthropic.com — set up billing and a workspace"
    echo "  spend cap first, then run:"
    echo
    echo "    read -rs \"k?Paste key: \" && printf 'export ANTHROPIC_API_KEY=%s\\n' \"\$k\" > ~/.anthropic-env && chmod 600 ~/.anthropic-env && unset k"
    echo
    exit 1
  fi
}

confirm() {
  echo
  printf '  About to spend money: %s. Continue? [y/N] ' "$1"
  read -r reply
  case "$reply" in [yY]*) ;; *) echo "  stopped."; exit 0 ;; esac
  echo
}

probe() {
  "$PY" "$SCRIPTS/probe.py" \
    --prompts  "$OUT/prompt-universe.json" \
    --identity "$OUT/identity.json" \
    --baseline --runs "$2" --out "$1" ${3:+--min-priority "$3"}
}

case "${1:-}" in

check)
  b "Answer Layer — check"
  ensure_venv
  "$PY" -c 'import anthropic,pydantic' && ok "venv + deps"
  for f in probe.py surface_check.py diff_harvest.py; do
    [ -f "$SCRIPTS/$f" ] && ok "scripts/$f" || no "scripts/$f MISSING"
  done
  for f in identity.json truth.json prompt-universe.json; do
    if [ -f "$OUT/$f" ]; then
      "$PY" -c "import json,sys; json.load(open(sys.argv[1]))" "$OUT/$f" \
        && ok "out/rebuild/$f" || no "out/rebuild/$f INVALID JSON"
    else no "out/rebuild/$f MISSING"; fi
  done
  n=$("$PY" -c "import json;print(len(json.load(open('$OUT/prompt-universe.json'))['prompts']))")
  ok "$n prompts in the frozen set"
  ls "$HERE/answer-layer/agents"/*.md >/dev/null 2>&1 \
    && ok "$(ls "$HERE/answer-layer/agents"/*.md | wc -l | tr -d ' ') agents"
  if [ -f "$KEYFILE" ]; then . "$KEYFILE"; fi
  [ -n "${ANTHROPIC_API_KEY:-}" ] \
    && ok "API key present (${#ANTHROPIC_API_KEY} chars)" \
    || hm "no API key yet — needed for smoke/probe/full, not for surface"
  echo; b "ready. next: ./run.sh smoke"
  ;;

smoke)
  ensure_venv; ensure_key
  b "smoke test — 2 prompts, 1 run"
  echo "  Watch for: a non-empty citation cartel, and Semrush/Ahrefs named."
  echo "  An EMPTY cartel means web-search parsing is broken — report it."
  confirm "~4 API calls, a few cents"
  probe /tmp/smoke.json 1 25
  ;;

probe)
  ensure_venv; ensure_key
  b "baseline probe — 10 prompts x 3 runs"
  confirm "~60 API calls, roughly \$5-12"
  probe "$OUT/harvest-$(date +%Y-%m).json" 3 16
  echo "  -> $OUT/harvest-$(date +%Y-%m).json"
  ;;

full)
  ensure_venv; ensure_key
  b "full baseline — 18 prompts x 3 runs"
  confirm "~108 API calls, roughly \$10-20"
  probe "$OUT/harvest-$(date +%Y-%m)-full.json" 3
  echo "  -> $OUT/harvest-$(date +%Y-%m)-full.json"
  ;;

surface)
  [ -z "${2:-}" ] && { echo "usage: ./run.sh surface <url> [extra flags]"; exit 1; }
  ensure_venv
  url="$2"; shift 2
  b "agent surface — $url"
  # ${1+"$@"} passes any remaining flags straight through (--json PATH,
  # --not-api-first) and stays safe under `set -u` on bash 3.2.
  "$PY" "$SCRIPTS/surface_check.py" "$url" ${1+"$@"}
  ;;

serve)
  PORT="${2:-8000}"
  b "serving site/ at http://localhost:$PORT"
  echo "  index    http://localhost:$PORT/"
  echo "  method   http://localhost:$PORT/method.html"
  echo "  work     http://localhost:$PORT/work.html"
  echo "  pricing  http://localhost:$PORT/pricing.html"
  echo "  index'd  http://localhost:$PORT/answer-index.html"
  echo
  echo "  ctrl-c to stop"
  cd "$HERE/site" && exec python3 -m http.server "$PORT"
  ;;

diff)
  [ -z "${3:-}" ] && { echo "usage: ./run.sh diff <old.json> <new.json> [extra flags]"; exit 1; }
  ensure_venv
  old="$2"; new="$3"; shift 3
  "$PY" "$SCRIPTS/diff_harvest.py" "$old" "$new" ${1+"$@"}
  ;;

*)
  sed -n "2,12p" "${BASH_SOURCE[0]}" | sed "s/^# \{0,1\}//"
  ;;
esac
