#!/bin/bash
# Resume the remaining-benches queue: MATH + LiveCodeBench (DROP/Veerman already done).
# Single server cap 65536; per-request caps via bench2. 0-OOM soak continues.
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
SLOG=$ROOT/.bench-logs/server-resume.log
DRIVER=$ROOT/.bench-logs/resume-mathlcb-driver.log
BASE=http://127.0.0.1:8765/v1
echo "=== resume start $(date -Iseconds) ===" >> "$DRIVER"
pkill -f mlx_lm.server; sleep 4; : > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 65536 --temp 0.0 --chat-template-args '{"enable_thinking":false}' >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up $(date -Iseconds) ===" >> "$DRIVER"
export LMSTUDIO_URL=$BASE BENCH_TIMEOUT=1800
cd "$ROOT/tools/local-llm-bench-m4-32gb"
echo "=== [math] START $(date -Iseconds) ===" >> "$DRIVER"
"$BENCHPY" scripts/bench2.py math --examples 100 --model "$MODEL" --max-tokens 4096 > "$ROOT/.bench-logs/rem-math.log" 2>&1
echo "=== [math] done rc=$? $(date -Iseconds) | metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"
echo "=== [livecodebench] START $(date -Iseconds) ===" >> "$DRIVER"
"$BENCHPY" scripts/bench2.py livecodebench --examples 50 --model "$MODEL" --lcb-version release_v6 --max-tokens 8192 > "$ROOT/.bench-logs/rem-livecodebench.log" 2>&1
echo "=== [livecodebench] done rc=$? $(date -Iseconds) | metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"
echo "=== RESUME DONE $(date -Iseconds) | total metal::malloc: $(grep -c metal::malloc "$SLOG") ===" >> "$DRIVER"
pkill -f mlx_lm.server
