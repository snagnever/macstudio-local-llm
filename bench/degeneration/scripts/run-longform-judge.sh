#!/bin/bash
# Coherence-judge the long-form degeneration outputs. Stops the DeepSeek server,
# loads the Qwen judge, rates all 48 saved generations 1-5, prints fail rates.
# Run AFTER run-degeneration-rates-longform.sh completes.
# Usage: nohup bash bench/degeneration/scripts/run-longform-judge.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
JUDGE_MODEL_DIR=/Users/vitor/.lmstudio/models/mlx-community/Qwen3.6-35B-A3B-6bit
JSLOG=$ROOT/bench/degeneration/logs/server-judge.log
LOG=$ROOT/bench/degeneration/logs/longform-judge.log
JUDGE_BASE=http://127.0.0.1:8766/v1
export JUDGE_BASE
export JUDGE_MODEL="$JUDGE_MODEL_DIR"
export IN="$ROOT/bench/degeneration/results/degeneration-rates-longform.jsonl"

: > "$LOG"
echo "=== long-form judge start $(date -Iseconds) ===" | tee -a "$LOG"
echo "--- stopping DeepSeek server to free memory for judge ---" | tee -a "$LOG"
pkill -f mlx_lm.server; sleep 6

: > "$JSLOG"
echo "--- starting judge: Qwen3.6-35B-A3B-6bit on :8766 ---" | tee -a "$LOG"
nohup "$PY" -m mlx_lm.server --model "$JUDGE_MODEL_DIR" --host 0.0.0.0 --port 8766 \
  --max-tokens 600 --temp 0.0 >> "$JSLOG" 2>&1 & disown
for i in $(seq 1 150); do curl -sf -m 5 "$JUDGE_BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$JUDGE_BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$JUDGE_MODEL_DIR\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== judge up $(date -Iseconds) ===" | tee -a "$LOG"

cd "$ROOT"
"$BENCHPY" bench/degeneration/scripts/judge_longform_coherence.py 2>&1 | tee -a "$LOG"
echo "=== judge done $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server
echo "(judge stopped. Restore DeepSeek DSML: bash fixes/deepseek-v4-flash/dsml/install.sh)" | tee -a "$LOG"
