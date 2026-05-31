#!/bin/bash
# End-to-end verification of the PoolingCache materialization fix:
# patched server + 20K-token forced-generation probe (baseline OOMs at 11,314).
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
LOG=$ROOT/.bench-logs/server-poolingfix.log

pkill -f mlx_lm.server; sleep 3
: > "$LOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" \
  --host 0.0.0.0 --port 8765 --max-tokens 65536 --temp 0.0 \
  >> "$LOG" 2>&1 & disown

# wait for HTTP up
for i in $(seq 1 90); do
  curl -sf -m 5 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && break
  sleep 2
done
echo "=== HTTP up after ${i} polls; warm-loading model ==="
curl -sS -m 600 http://127.0.0.1:8765/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" \
  >/dev/null && echo "=== warm-load OK ==="

echo "=== running repro_oom_gen.py (20K tokens) ==="
"$PY" "$ROOT/.bench-logs/repro_oom_gen.py" --max-tokens 20000 2>&1 \
  | tee "$ROOT/.bench-logs/repro-poolingfix-gen.log"

echo "=== metal::malloc errors in server log: $(grep -c 'metal::malloc' "$LOG") ==="
pkill -f mlx_lm.server
echo "=== server stopped ==="
