#!/bin/bash
# Native DSML tool-calling bench for DeepSeek-V4-Flash (thinking OFF), vs Hermes 33/40, 6/12.
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
SLOG=$ROOT/bench/deepseek-v4-flash/logs/server-dsml.log
LOG=$ROOT/bench/deepseek-v4-flash/logs/dsml-bench.log
BASE=http://127.0.0.1:8765/v1
: > "$LOG"; pkill -f mlx_lm.server; sleep 3; : > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 2048 --temp 0.0 --chat-template-args '{"thinking_mode":"chat"}' >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up (DSML, thinking off) $(date -Iseconds) ===" | tee -a "$LOG"
cd "$ROOT/tools/local-llm-bench-m4-32gb"
echo "=== VEERMAN (Hermes was 6/12) ===" | tee -a "$LOG"
"$BENCHPY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman --base-url "$BASE" \
  --force --no-cooldown --run-prefix dsml 2>&1 | tail -3 | tee -a "$LOG"
echo "=== JDHODGES (Hermes was 33/40) ===" | tee -a "$LOG"
"$BENCHPY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges --base-url "$BASE" \
  --force --no-cooldown --run-prefix dsml 2>&1 | tail -3 | tee -a "$LOG"
echo "=== metal::malloc: $(grep -c metal::malloc "$SLOG") | done $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server
