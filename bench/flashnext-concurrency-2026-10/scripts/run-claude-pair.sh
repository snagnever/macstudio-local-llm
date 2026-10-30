#!/usr/bin/env bash
# One or two non-interactive Claude Code sessions (claude -p) against the local driver, each on a fresh copy of a
# fixed task repository. Writes results/cc-<tag>-<task>.json = claude's result object + wall_s, task, sessions,
# exit, task_done (a hidden check of the work, run after the session), parallel_agent_calls, subagents_spawned,
# subagents. With --proxy, each session talks to its own request_log.py proxy and the per-request records land in
# results/req-<tag>-<task>.jsonl (one shared clock for the sessions of one run).
# usage: run-claude-pair.sh --sessions 1|2 --tag TAG [--task a|b|c|d] [--pair a,b|c,d] [--subagents]
#                           [--proxy BASEPORT] [--max-turns N] [--out DIR] [--dry-run]
#        run-claude-pair.sh --interactive-env      (prints the exports for a manual interactive session)
# Env: BASE_URL and MODEL_ID (from run-candidate.sh --exec), CLAUDE_BIN, CLAUDE_PAIR_WORK, CLAUDE_PAIR_TIMEOUT,
# CLAUDE_PAIR_RAW_DIR.
# bash 3.2 (the rig's).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKS="$HERE/claude-tasks"
SESSIONS=""; TAG=""; TASK=a; PAIR="a,b"; SUBAGENTS=""; PROXY=""; MAX_TURNS=""
OUT="$(cd "$HERE/.." && pwd)/results"; DRY=""; IENV=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sessions) SESSIONS="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --task) TASK="$2"; shift 2 ;;
    --pair) PAIR="$2"; shift 2 ;;
    --subagents) SUBAGENTS=1; shift ;;
    --proxy) PROXY="$2"; shift 2 ;;
    --max-turns) MAX_TURNS="$2"; shift 2 ;;
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
RAW_DIR="${CLAUDE_PAIR_RAW_DIR:-}"  # with --proxy: keep every response's raw SSE under this dir (debugging)

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
[[ "$TASK" == a || "$TASK" == b || "$TASK" == c || "$TASK" == d ]] || { echo "run-claude-pair: --task a|b|c|d" >&2; exit 64; }
[[ "$PAIR" == "a,b" || "$PAIR" == "c,d" ]] || { echo "run-claude-pair: --pair a,b|c,d" >&2; exit 64; }
[[ -z "$PROXY" || "$PROXY" =~ ^[0-9]+$ ]] || { echo "run-claude-pair: --proxy BASEPORT (integer)" >&2; exit 64; }
[[ -z "$MAX_TURNS" || "$MAX_TURNS" =~ ^[0-9]+$ ]] || { echo "run-claude-pair: --max-turns N (integer)" >&2; exit 64; }
if [[ "$SESSIONS" == 2 ]]; then RUN_TASKS=(${PAIR//,/ }); else RUN_TASKS=("$TASK"); fi
# Small tasks (a, b) fit in 40 turns; the realistic ones (c, d) get 60.
if [[ -z "$MAX_TURNS" ]]; then
  MAX_TURNS=40
  for t in "${RUN_TASKS[@]}"; do [[ "$t" == c || "$t" == d ]] && MAX_TURNS=60; done
fi

# Project settings only (the copy has none) and no MCP servers: user hooks and plugins stay out of the run.
# stream-json keeps every assistant message (to count parallel Agent calls); the result object is the last line.
TOOLS=(Read Edit Write Glob Grep)
[[ -n "$SUBAGENTS" ]] && TOOLS=("${TOOLS[@]}" Agent)
TOOLS=("${TOOLS[@]}" "Bash(python3:*)" "Bash(bash:*)" "Bash(ls:*)" "Bash(cat:*)" "Bash(git status:*)" "Bash(git diff:*)")
CLAUDE_ARGS=(--output-format stream-json --verbose --setting-sources project --strict-mcp-config
  --permission-mode default --max-turns "$MAX_TURNS" --allowedTools "${TOOLS[@]}")

prompt_files() {  # $1 = task. The files whose concatenation is the prompt.
  if [[ -n "$SUBAGENTS" ]]; then echo "$TASKS/subagents-preamble.md $TASKS/task-$1.md"; else echo "$TASKS/task-$1.md"; fi
}

proxy_port() { echo $((PROXY + $1)); }  # $1 = session index (0, 1)

if [[ -n "$DRY" ]]; then
  for l in "${ENV_LINES[@]}"; do echo "$l"; done
  i=0
  for t in "${RUN_TASKS[@]}"; do
    if [[ -n "$PROXY" ]]; then
      port="$(proxy_port "$i")"
      echo "python3 $HERE/request_log.py --listen $port --upstream $ANTHROPIC_URL --out $OUT/req-$TAG-$t.jsonl --stream $TAG-$t --t0 \$T0${RAW_DIR:+ --raw-dir $RAW_DIR} &"
      echo "ANTHROPIC_BASE_URL=http://127.0.0.1:$port"
    fi
    echo "cd $WORK/$TAG-$t && claude -p \"\$(cat $(prompt_files "$t"))\" ${CLAUDE_ARGS[*]}"
    i=$((i + 1))
  done
  exit 0
fi

task_done() {  # $1 = task, $2 = repo copy. Prints true/false.
  local t="$1" repo="$2" tmp
  if [[ "$t" == c || "$t" == d ]]; then
    bash "$TASKS/check-$t.sh" "$repo" 2>/dev/null || echo false
    return 0
  fi
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

wait_port() {  # $1 = port. Returns 0 once something listens on 127.0.0.1:$1 (up to 10 s).
  local n=0
  while [[ $n -lt 100 ]]; do
    python3 -c 'import socket,sys; s=socket.socket(); s.settimeout(0.2); s.connect(("127.0.0.1", int(sys.argv[1]))); s.close()' "$1" 2>/dev/null && return 0
    sleep 0.1; n=$((n + 1))
  done
  return 1
}

mkdir -p "$OUT" "$WORK"
T0=$(python3 -c 'import time; print(time.time())')  # one clock for every session (and proxy) of this run
PIDS=()
i=0
for t in "${RUN_TASKS[@]}"; do
  repo="$WORK/$TAG-$t"
  port=""; [[ -n "$PROXY" ]] && port="$(proxy_port "$i")"
  rm -rf "$repo"; cp -R "$TASKS/repo-$t" "$repo"
  (cd "$repo" && git init -q && git add -A && git -c user.name=bench -c user.email=bench@localhost commit -qm base)
  mkdir -p "$repo.config"
  (
    cd "$repo"
    for l in "${ENV_LINES[@]}"; do export "$l"; done
    export CLAUDE_CONFIG_DIR="$repo.config"
    ppid=""
    if [[ -n "$port" ]]; then
      rm -f "$OUT/req-$TAG-$t.jsonl"
      python3 "$HERE/request_log.py" --listen "$port" --upstream "$ANTHROPIC_URL" --out "$OUT/req-$TAG-$t.jsonl" \
        --stream "$TAG-$t" --t0 "$T0" ${RAW_DIR:+--raw-dir "$RAW_DIR"} 2> "$repo.proxy.log" &
      ppid=$!
      wait_port "$port" || echo "    task $t: proxy on $port did not come up" >&2
      export ANTHROPIC_BASE_URL="http://127.0.0.1:$port"
    fi
    t0=$(python3 -c 'import time; print(time.time())')
    rc=0
    "$CLAUDE_BIN" -p "$(cat $(prompt_files "$t"))" "${CLAUDE_ARGS[@]}" > "$repo.out.json" 2> "$repo.err.log" &
    cpid=$!
    # Watchdog by polling: a backgrounded sleep would keep this subshell's stdout open after a kill.
    waited=0
    while kill -0 "$cpid" 2>/dev/null; do
      if [[ "$waited" -ge "$TIMEOUT" ]]; then kill "$cpid" 2>/dev/null || true; break; fi
      sleep 1; waited=$((waited + 1))
    done
    wait "$cpid" || rc=$?
    t1=$(python3 -c 'import time; print(time.time())')
    if [[ -n "$ppid" ]]; then kill "$ppid" 2>/dev/null || true; wait "$ppid" 2>/dev/null || true; fi
    done_flag="$(task_done "$t" "$repo")"
    python3 - "$repo.out.json" "$OUT/cc-$TAG-$t.json" "$t" "$SESSIONS" "$rc" "$t0" "$t1" "$done_flag" "${SUBAGENTS:-0}" <<'PY'
import json, sys
src, dst, task, sessions, rc, t0, t1, done, subagents = sys.argv[1:]
data, parallel, spawned = None, 0, 0
try:
    for line in open(src, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if not isinstance(msg, dict):
            continue
        if msg.get("type") == "result":
            data = msg
        elif msg.get("type") == "assistant":
            content = (msg.get("message") or {}).get("content") or []
            n = sum(1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Agent")
            if n >= 2:
                parallel += 1
except OSError:
    pass
if data is None:
    data = {"parse_error": True}
stats = data.get("subagent_stats") or {}
spawned = int(stats.get("spawned") or 0)
data.update({"task": task, "sessions": int(sessions), "exit": int(rc),
             "wall_s": round(float(t1) - float(t0), 1), "task_done": done == "true",
             "parallel_agent_calls": parallel, "subagents_spawned": spawned, "subagents": subagents == "1"})
json.dump(data, open(dst, "w", encoding="utf-8"), indent=2)
PY
    echo "    task $t exit $rc wall $(python3 -c "print(round($t1-$t0,1))") s task_done $done_flag"
    [[ "$rc" -eq 0 && "$done_flag" == true ]]
  ) & PIDS+=($!)
  i=$((i + 1))
done

FAILED=0
for p in "${PIDS[@]}"; do rc=0; wait "$p" || rc=$?; [[ "$rc" -ne 0 ]] && FAILED=1; done
exit "$FAILED"
