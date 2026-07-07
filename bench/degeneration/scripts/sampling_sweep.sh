#!/bin/bash
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
LOG=$ROOT/bench/degeneration/logs/server-sampling-sweep.log

pkill -f mlx_lm.server; sleep 3
: > "$LOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 \
  --chat-template-args '{"enable_thinking":false}' \
  >> "$LOG" 2>&1 & disown

for i in $(seq 1 90); do
  curl -sf -m 5 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && break
  sleep 2
done
echo "=== HTTP up; warm-loading ==="
curl -sS -m 600 http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" \
  >/dev/null && echo "=== warm-load OK ==="

echo "=== sampling sweep on 'você executa código' (enable_thinking=false) ==="
"$PY" "$ROOT/bench/degeneration/scripts/sampling_sweep.py"

echo "=== metal::malloc errors: $(grep -c 'metal::malloc' "$LOG") ==="
pkill -f mlx_lm.server
echo "=== server stopped ==="
