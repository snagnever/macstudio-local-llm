#!/usr/bin/env bash
# Etapa 2: one or two non-interactive Claude Code sessions (claude -p) against the local driver, each on a fresh
# copy of a fixed task repository. Writes results/cc-<tag>-<task>.json = claude's JSON result + wall_s, task,
# sessions, exit and task_done (a hidden check of the work, run after the session).
# usage: run-claude-pair.sh --sessions 1|2 --tag TAG [--task a|b] [--out DIR] [--dry-run]
#        run-claude-pair.sh --interactive-env      (prints the exports for a manual interactive session)
# Env: BASE_URL and MODEL_ID (from run-candidate.sh --exec), CLAUDE_BIN, CLAUDE_PAIR_WORK, CLAUDE_PAIR_TIMEOUT.
# bash 3.2 (the rig's).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKS="$HERE/claude-tasks"
SESSIONS=""; TAG=""; TASK=a; OUT="$(cd "$HERE/.." && pwd)/results"; DRY=""; IENV=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sessions) SESSIONS="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --task) TASK="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --interactive-env) IENV=1; shift ;;
    *) echo "run-claude-pair: unknown option: $1" >&2; exit 64 ;;
  esac
done

BASE_URL="${BASE_URL:-http://127.0.0.1:11234/v1}"
ANTHROPIC_URL="${BASE_URL%/v1}"
MODEL_ID="${MODEL_ID:-Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
WORK="${CLAUDE_PAIR_WORK:-$HOME/.cache/flashnext-concurrency/claude-work}"
TIMEOUT="${CLAUDE_PAIR_TIMEOUT:-1800}"

ENV_LINES=(
  "ANTHROPIC_BASE_URL=$ANTHROPIC_URL" "ANTHROPIC_AUTH_TOKEN=local"
  "ANTHROPIC_MODEL=$MODEL_ID" "ANTHROPIC_DEFAULT_HAIKU_MODEL=$MODEL_ID" "ANTHROPIC_SMALL_FAST_MODEL=$MODEL_ID"
  "CLAUDE_CODE_EFFORT_LEVEL=xhigh" "DISABLE_TELEMETRY=1" "DISABLE_AUTOUPDATER=1"
)
if [[ -n "$IENV" ]]; then
  for l in "${ENV_LINES[@]}"; do echo "export $l"; done
  exit 0
fi
[[ "$SESSIONS" == 1 || "$SESSIONS" == 2 ]] || { echo "run-claude-pair: --sessions 1|2 required" >&2; exit 64; }
[[ -n "$TAG" ]] || { echo "run-claude-pair: --tag required" >&2; exit 64; }
[[ "$TASK" == a || "$TASK" == b ]] || { echo "run-claude-pair: --task a|b" >&2; exit 64; }
if [[ "$SESSIONS" == 2 ]]; then RUN_TASKS=(a b); else RUN_TASKS=("$TASK"); fi

# Project settings only (the copy has none) and no MCP servers: user hooks and plugins stay out of the run.
CLAUDE_ARGS=(--output-format json --setting-sources project --strict-mcp-config --permission-mode default
  --max-turns 40
  --allowedTools Read Edit Write Glob Grep "Bash(python3:*)" "Bash(bash:*)" "Bash(ls:*)" "Bash(cat:*)"
  "Bash(git status:*)" "Bash(git diff:*)")

if [[ -n "$DRY" ]]; then
  for l in "${ENV_LINES[@]}"; do echo "$l"; done
  for t in "${RUN_TASKS[@]}"; do
    echo "cd $WORK/$TAG-$t && claude -p \"\$(cat $TASKS/task-$t.md)\" ${CLAUDE_ARGS[*]}"
  done
  exit 0
fi

task_done() {  # $1 = task, $2 = repo copy. Prints true/false.
  local t="$1" repo="$2" tmp
  tmp="$(mktemp -d)"
  if [[ "$t" == a ]]; then
    printf 'name,qty,price\nbolt,4,0.25\nnut,10,0.1\n' > "$tmp/inv.csv"
    if (cd "$repo" && python3 -m unittest discover -s tests -t . >/dev/null 2>&1) &&
       (cd "$repo" && python3 -m inventory.cli --format json "$tmp/inv.csv" 2>/dev/null) |
       python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("items")==2 and abs(float(d.get("total"))-2.0)<1e-9 else 1)' 2>/dev/null
    then echo true; else echo false; fi
  else
    printf 'a b c d e f g h i j\n' > "$tmp/ten words.txt"; printf 'a b c d e f g h i\n' > "$tmp/nine.txt"
    local got want ntests
    got="$(bash "$repo/wc_report.sh" "$tmp" 2>/dev/null || true)"
    want="10 ten words.txt
9 nine.txt"
    ntests="$(grep -c '^check ' "$repo/tests/run_tests.sh" 2>/dev/null || echo 0)"
    if [[ "$got" == "$want" && "$ntests" -ge 3 ]] && (cd "$repo" && bash tests/run_tests.sh >/dev/null 2>&1)
    then echo true; else echo false; fi
  fi
  rm -rf "$tmp"
}

mkdir -p "$OUT" "$WORK"
PIDS=()
for t in "${RUN_TASKS[@]}"; do
  repo="$WORK/$TAG-$t"
  rm -rf "$repo"; cp -R "$TASKS/repo-$t" "$repo"
  (cd "$repo" && git init -q && git add -A && git -c user.name=bench -c user.email=bench@localhost commit -qm base)
  mkdir -p "$repo.config"
  (
    cd "$repo"
    for l in "${ENV_LINES[@]}"; do export "$l"; done
    export CLAUDE_CONFIG_DIR="$repo.config"
    t0=$(python3 -c 'import time; print(time.time())')
    rc=0
    "$CLAUDE_BIN" -p "$(cat "$TASKS/task-$t.md")" "${CLAUDE_ARGS[@]}" > "$repo.out.json" 2> "$repo.err.log" &
    cpid=$!
    # Watchdog by polling: a backgrounded sleep would keep this subshell's stdout open after a kill.
    waited=0
    while kill -0 "$cpid" 2>/dev/null; do
      if [[ "$waited" -ge "$TIMEOUT" ]]; then kill "$cpid" 2>/dev/null || true; break; fi
      sleep 1; waited=$((waited + 1))
    done
    wait "$cpid" || rc=$?
    t1=$(python3 -c 'import time; print(time.time())')
    done_flag="$(task_done "$t" "$repo")"
    python3 - "$repo.out.json" "$OUT/cc-$TAG-$t.json" "$t" "$SESSIONS" "$rc" "$t0" "$t1" "$done_flag" <<'PY'
import json, sys
src, dst, task, sessions, rc, t0, t1, done = sys.argv[1:]
try:
    text = open(src, encoding="utf-8").read().strip()
    data = json.loads(text.splitlines()[-1]) if text else {}
except (OSError, ValueError, IndexError):
    data = {"parse_error": True}
data.update({"task": task, "sessions": int(sessions), "exit": int(rc),
             "wall_s": round(float(t1) - float(t0), 1), "task_done": done == "true"})
json.dump(data, open(dst, "w", encoding="utf-8"), indent=2)
PY
    echo "    task $t exit $rc wall $(python3 -c "print(round($t1-$t0,1))") s task_done $done_flag"
    [[ "$rc" -eq 0 && "$done_flag" == true ]]
  ) & PIDS+=($!)
done

FAILED=0
for p in "${PIDS[@]}"; do rc=0; wait "$p" || rc=$?; [[ "$rc" -ne 0 ]] && FAILED=1; done
exit "$FAILED"
