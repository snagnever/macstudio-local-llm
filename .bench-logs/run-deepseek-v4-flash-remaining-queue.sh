#!/bin/bash
# Remaining-benches queue for DeepSeek-V4-Flash, shortest->biggest, on the patched
# runtime. Covers the 4 harness-identical benches (Veerman, DROP, MATH, LiveCodeBench);
# throughput + Terminal-Bench are handled separately (different harnesses / Docker).
# Plan: docs/benchmark-plans/2026-05-30-deepseek-v4-flash-remaining-benches.md
#
# tool_call_bench.py sends NO max_tokens -> Veerman is bounded only by the server
# --max-tokens, so it runs on a 2048-cap server; bench2 then runs on a 65536-ceiling
# server so its per-request caps (2048/4096/8192) apply. temp=0, thinking=OFF.
#   Pass: 0 'metal::malloc' in SLOG across the whole queue.
# Usage: nohup bash .bench-logs/run-deepseek-v4-flash-remaining-queue.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
SLOG=$ROOT/.bench-logs/server-remaining.log
DRIVER=$ROOT/.bench-logs/remaining-queue-driver.log
BASE=http://127.0.0.1:8765/v1

echo "=== queue start $(date -Iseconds) ===" >> "$DRIVER"
: > "$SLOG"

start_server() {  # $1 = max-tokens ceiling
  pkill -f mlx_lm.server; sleep 4
  nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
    --max-tokens "$1" --temp 0.0 --chat-template-args '{"enable_thinking":false}' \
    >> "$SLOG" 2>&1 & disown
  for i in $(seq 1 120); do
    curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2
  done
  curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" \
    >/dev/null 2>&1
  echo "=== server up (cap=$1) after ${i} polls $(date -Iseconds) ===" >> "$DRIVER"
}

export LMSTUDIO_URL=$BASE
export BENCH_TIMEOUT=1800
cd "$ROOT/tools/local-llm-bench-m4-32gb"

# ---- 1. Veerman (server cap 2048; tool_call_bench has no own cap) ----
start_server 2048
echo "=== [veerman] START $(date -Iseconds) ===" >> "$DRIVER"
"$BENCHPY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman \
  --base-url "$BASE" --force --no-cooldown --run-prefix toolcall \
  > "$ROOT/.bench-logs/rem-veerman.log" 2>&1
echo "=== [veerman] done rc=$? $(date -Iseconds) | metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"

# ---- 2-4. bench2 group (server ceiling 65536; per-request caps apply) ----
start_server 65536
run2() {  # $1 name $2 bench $3 examples $4 maxtok
  echo "=== [$1] START $(date -Iseconds) ===" >> "$DRIVER"
  "$BENCHPY" scripts/bench2.py "$2" --examples "$3" --model "$MODEL" --max-tokens "$4" \
    > "$ROOT/.bench-logs/rem-$1.log" 2>&1
  echo "=== [$1] done rc=$? $(date -Iseconds) | metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"
}
run2 drop drop 100 2048
run2 math math 100 4096
# LiveCodeBench v6 (needs --lcb-version)
echo "=== [livecodebench] START $(date -Iseconds) ===" >> "$DRIVER"
"$BENCHPY" scripts/bench2.py livecodebench --examples 50 --model "$MODEL" \
  --lcb-version release_v6 --max-tokens 8192 \
  > "$ROOT/.bench-logs/rem-livecodebench.log" 2>&1
echo "=== [livecodebench] done rc=$? $(date -Iseconds) | metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"

echo "=== QUEUE DONE $(date -Iseconds) | total metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"
pkill -f mlx_lm.server
echo "=== server stopped $(date -Iseconds) ===" >> "$DRIVER"
