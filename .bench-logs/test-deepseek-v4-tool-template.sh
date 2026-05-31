#!/bin/bash
# Live test for the DeepSeek-V4-Flash tool template. Run AFTER the benchmark queue
# completes (it stops any running server). Installs the template, starts a server,
# checks detection, runs a tool-emission probe + the 12-case Veerman suite.
# Usage: nohup bash .bench-logs/test-deepseek-v4-tool-template.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
SLOG=$ROOT/.bench-logs/server-tooltmpl.log
LOG=$ROOT/.bench-logs/tool-template-test.log
BASE=http://127.0.0.1:8765/v1

: > "$LOG"; : > "$SLOG"
echo "=== tool-template test start $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server; pkill -f bench2.py; pkill -f tool_call_bench.py; sleep 4

echo "--- installing tool template ---" | tee -a "$LOG"
bash "$ROOT/assets/deepseek-v4-tool-template/install.sh" 2>&1 | tee -a "$LOG"

nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 2048 --temp 0.0 --chat-template-args '{"enable_thinking":false}' \
  >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up $(date -Iseconds) ===" | tee -a "$LOG"

echo "--- DETECTION: 'does not support tool calling' warnings (want 0) ---" | tee -a "$LOG"
sleep 1; grep -c "does not support tool calling" "$SLOG" | tee -a "$LOG"

echo "--- EMISSION: tool probe ---" | tee -a "$LOG"
BASE="$BASE" MODEL="$MODEL" "$BENCHPY" "$ROOT/assets/deepseek-v4-tool-template/tool_probe.py" 2>&1 | tee -a "$LOG"

echo "--- Veerman suite (was 2/12 without template) ---" | tee -a "$LOG"
cd "$ROOT/tools/local-llm-bench-m4-32gb"
"$BENCHPY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman \
  --base-url "$BASE" --force --no-cooldown --run-prefix toolcall_tooltmpl 2>&1 | tail -25 | tee -a "$LOG"

echo "=== metal::malloc in server log: $(grep -c metal::malloc "$SLOG") ===" | tee -a "$LOG"
echo "=== test done $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server
echo "(template still installed; run assets/deepseek-v4-tool-template/uninstall.sh to revert)" | tee -a "$LOG"
