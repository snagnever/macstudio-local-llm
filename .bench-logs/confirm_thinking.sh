#!/bin/bash
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
LOG=$ROOT/.bench-logs/server-confirm-thinking.log

run_with() {  # $1 = chat-template-args, $2 = label
  pkill -f mlx_lm.server; sleep 3
  : > "$LOG"
  if [ -n "$1" ]; then EXTRA=(--chat-template-args "$1"); else EXTRA=(); fi
  nohup "$PY" -m mlx_lm.server --model "$MODEL" \
    --host 0.0.0.0 --port 8765 --max-tokens 65536 "${EXTRA[@]}" \
    >> "$LOG" 2>&1 & disown
  for i in $(seq 1 90); do
    curl -sf -m 5 http://127.0.0.1:8765/v1/models >/dev/null 2>&1 && break; sleep 2
  done
  curl -sS -m 600 http://127.0.0.1:8765/v1/chat/completions -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null
  echo "================= $2 ================="
  "$PY" "$ROOT/.bench-logs/confirm_thinking.py" "$2"
}

run_with '{"enable_thinking":true}'  "thinking=ON"
run_with '{"enable_thinking":false}' "thinking=OFF"
run_with ''                          "thinking=DEFAULT(no flag = your WebUI cmd)"

pkill -f mlx_lm.server
echo "=== metal::malloc errors across run: $(grep -c 'metal::malloc' "$LOG") ==="
echo "=== server stopped ==="
