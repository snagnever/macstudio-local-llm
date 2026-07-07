#!/bin/bash
# Long-form stochastic COLLAPSE-rate measurement (real seeds, #1331 fix in place).
# story_en (800w) + list_en (50-item), 8 seeds, 2048-tok budget. Collapse is judged
# from content (tail-loop / low distinct), NOT finish=length — a coherent answer that
# hits the cap is not a loop. 3 configs: baseline / no-XTC / +XTC.
# Usage: nohup bash bench/degeneration/scripts/run-degeneration-rates-longform.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
ORIG=$ROOT/fixes/deepseek-v4-flash/tool-template/original
SLOG=$ROOT/bench/degeneration/logs/server-degeneration.log
LOG=$ROOT/bench/degeneration/logs/degeneration-rates-longform.log
BASE=http://127.0.0.1:8765/v1
export BASE MODEL

: > "$LOG"
echo "=== long-form RATES run start $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server; pkill -f bench2.py; sleep 4

echo "--- restoring pristine plain chat template ---" | tee -a "$LOG"
cp "$ORIG/chat_template.jinja"    "$MODEL/chat_template.jinja"
cp "$ORIG/tokenizer_config.json"  "$MODEL/tokenizer_config.json"
echo "template now: $(wc -l < "$MODEL/chat_template.jinja") lines (24=plain)" | tee -a "$LOG"

: > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 2048 --temp 0.0 >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up (seed fix loaded) $(date -Iseconds) ===" | tee -a "$LOG"

cd "$ROOT"
export ONLY="ctrl_t0.6,abl_noxtc,combo_xtc_presence"
export PROMPTS_ONLY="story_en,list_en"
export SEEDS="0,1,2,3,4,5,6,7"
export MAXTOK=2048
export OUT="$ROOT/bench/degeneration/results/degeneration-rates-longform.jsonl"
echo "--- long-form sweep: 3 configs x 2 prompts x 8 seeds, 2048 tok ---" | tee -a "$LOG"
"$BENCHPY" bench/degeneration/scripts/degeneration_sweep.py screen 2>&1 | tee -a "$LOG"

echo "=== metal::malloc in server log: $(grep -c metal::malloc "$SLOG") (want 0) ===" | tee -a "$LOG"
echo "=== long-form rates run done $(date -Iseconds) ===" | tee -a "$LOG"
echo "(server left up. Restore DSML: pkill -f mlx_lm.server && bash fixes/deepseek-v4-flash/dsml/install.sh)" | tee -a "$LOG"
