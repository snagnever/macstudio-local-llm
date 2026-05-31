#!/bin/bash
# Pre-PR OOM soak + degeneration probe for the DeepSeek-V4 cache-materialize fix.
# ONE long-lived patched server (no restart wrapper) — the whole point is to prove
# the residency leak stays bounded across hundreds of varied requests, the same
# cross-request accumulation that used to OOM at jdhodges case 20.
#
#   Pass (OOM):          0 'metal::malloc' in the server log, all 3 benches complete.
#   Degeneration signal: bench2 reports ">>> N questions truncated" = the 2-bit
#                        quant quality floor (separate from the leak; expected, not
#                        a fix failure). temp=0 greedy is the standard bench setting.
#
# max_tokens capped per-bench (2048/4096) so any degenerate runaway is bounded to
# ~70-140s instead of grinding to the 65536 ceiling. thinking=OFF (established
# baseline). Usage:
#   nohup bash .bench-logs/run-deepseek-v4-flash-knowledge-soak.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python      # patched mlx-lm server venv
BENCHPY=$ROOT/.venv/bin/python              # bench client venv
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
LOG=$ROOT/.bench-logs/server-knowledge-soak.log
DRIVER=$ROOT/.bench-logs/knowledge-soak-driver.log

echo "=== driver start $(date -Iseconds) ===" >> "$DRIVER"
pkill -f mlx_lm.server; sleep 3
: > "$LOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  --chat-template-args '{"enable_thinking":false}' \
  >> "$LOG" 2>&1 & disown

for i in $(seq 1 120); do
  curl -sf -m 5 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && break
  sleep 2
done
echo "=== HTTP up after ${i} polls; warm-loading $(date -Iseconds) ===" >> "$DRIVER"
curl -sS -m 600 http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" \
  >/dev/null && echo "=== warm-load OK $(date -Iseconds) ===" >> "$DRIVER"

export LMSTUDIO_URL=http://127.0.0.1:8765/v1
export BENCH_TIMEOUT=1800
cd "$ROOT/tools/local-llm-bench-m4-32gb"

run() {  # name  bench  examples  maxtok
  local name=$1 bench=$2 ex=$3 mt=$4
  local rl=$ROOT/.bench-logs/soak-${name}.log
  echo "=== [$name] $bench n=$ex max_tokens=$mt START $(date -Iseconds) ===" >> "$DRIVER"
  "$BENCHPY" scripts/bench2.py "$bench" --examples "$ex" --model "$MODEL" --max-tokens "$mt" \
    > "$rl" 2>&1
  echo "=== [$name] done rc=$? $(date -Iseconds) | metal::malloc so far: $(grep -c metal::malloc "$LOG") ===" >> "$DRIVER"
}

run mmlu      mmlu      100 2048
run gpqa      gpqa      100 4096
run humaneval humaneval 100 4096

echo "=== ALL DONE $(date -Iseconds) | total metal::malloc in server log: $(grep -c metal::malloc "$LOG") ===" >> "$DRIVER"
pkill -f mlx_lm.server
echo "=== server stopped $(date -Iseconds) ===" >> "$DRIVER"
