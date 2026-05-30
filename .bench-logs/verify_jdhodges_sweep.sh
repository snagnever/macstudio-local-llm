#!/bin/bash
# Done-bar #1: full 40-case jdhodges tool-call sweep on a SINGLE long-lived
# patched server (no restart wrapper). Unpatched baseline: 5/40, 49 Metal OOMs.
# Pass: 0 metal::malloc in the server log, sweep completes without wedging.
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
LOG=$ROOT/.bench-logs/server-cachefix-jdhodges.log
BENCHLOG=$ROOT/.bench-logs/jdhodges-cachefix.log

pkill -f mlx_lm.server; sleep 3
: > "$LOG"
# max-tokens capped at 2048: the model loops at temp=0.0 (separate known issue),
# and done-bar #1 tests cross-request cache accumulation (the case-20 OOM), which
# does not need full-length generations. Caps runaway cases to ~70s each.
nohup "$PY" -m mlx_lm.server --model "$MODEL" \
  --host 0.0.0.0 --port 8765 --max-tokens 2048 --temp 0.0 \
  >> "$LOG" 2>&1 & disown

for i in $(seq 1 90); do
  curl -sf -m 5 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && break
  sleep 2
done
echo "=== HTTP up after ${i} polls; warm-loading ==="
curl -sS -m 600 http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" \
  >/dev/null && echo "=== warm-load OK ==="

echo "=== jdhodges 40-case sweep on single long-lived server ==="
cd "$ROOT/tools/local-llm-bench-m4-32gb"
"$BENCHPY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges \
  --base-url http://127.0.0.1:8765/v1 --force --no-cooldown --run-prefix toolcall_cachefix \
  2>&1 | tee "$BENCHLOG"

echo "=== metal::malloc errors in server log: $(grep -c 'metal::malloc' "$LOG") ==="
pkill -f mlx_lm.server
echo "=== server stopped ==="
