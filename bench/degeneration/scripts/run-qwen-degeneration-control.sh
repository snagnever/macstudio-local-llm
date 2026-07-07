#!/bin/bash
# Free cross-precision control: does a HIGH-precision model loop on the same
# degeneration prompts? Runs the rate harness on Qwen3.6-35B-A3B 6-bit then 8-bit
# (MLX, both local; seed fix already in this venv), thinking OFF, 8 seeds.
# Expectation: ~0% loop -> degeneration is a low-bit effect, not harness/prompt.
# Usage: nohup bash bench/degeneration/scripts/run-qwen-degeneration-control.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
BASE=http://127.0.0.1:8765/v1
LOG=$ROOT/bench/degeneration/logs/qwen-control.log
export BASE
export ONLY="ctrl_t0.6"
export PROMPTS_ONLY="exec_pt,story_en,qa_fact"
export SEEDS="0,1,2,3,4,5,6,7"
export MAXTOK=2048
export CHAT_KWARGS='{"enable_thinking": false}'

: > "$LOG"
echo "=== Qwen degeneration control start $(date -Iseconds) ===" | tee -a "$LOG"
for tag in 6bit 8bit; do
  MODEL="$HOME/.lmstudio/models/mlx-community/Qwen3.6-35B-A3B-$tag"
  SLOG=$ROOT/bench/degeneration/logs/server-qwen-$tag.log
  echo "──────── Qwen3.6-35B-A3B-$tag ────────" | tee -a "$LOG"
  pkill -f mlx_lm.server; sleep 4
  : > "$SLOG"
  nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
    --max-tokens 2048 --temp 0.0 >> "$SLOG" 2>&1 & disown
  for i in $(seq 1 150); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
  curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
  echo "=== server up ($tag) $(date -Iseconds) ===" | tee -a "$LOG"
  MODEL="$MODEL" OUT="$ROOT/bench/degeneration/logs/qwen-$tag-degeneration.jsonl" \
    "$BENCHPY" bench/degeneration/scripts/degeneration_sweep.py screen 2>&1 | tee -a "$LOG"
done
pkill -f mlx_lm.server
echo "=== Qwen control done $(date -Iseconds) ===" | tee -a "$LOG"
