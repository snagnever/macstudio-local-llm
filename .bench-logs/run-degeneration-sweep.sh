#!/bin/bash
# Degeneration sampling sweep for DeepSeek-V4-Flash-2bit-DQ.
# Tests XTC + presence_penalty (the two knobs we never tried) against the
# long-form repetition loop. Restores the PRISTINE plain chat template first so we
# measure the default chat path the HF thread is about (apples-to-apples with the
# earlier sweep), then re-enable DSML at the end.
#
# Usage: nohup bash .bench-logs/run-degeneration-sweep.sh screen >/dev/null 2>&1 & disown
#        (pass "confirm" to run survivors over all prompts x 5 seeds; set SURVIVORS=a,b,c)
set -u
PHASE="${1:-screen}"
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
ORIG=$ROOT/assets/deepseek-v4-tool-template/original
SLOG=$ROOT/.bench-logs/server-degeneration.log
LOG=$ROOT/.bench-logs/degeneration-${PHASE}.log
BASE=http://127.0.0.1:8765/v1
export BASE MODEL

: > "$LOG"
echo "=== degeneration sweep ($PHASE) start $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server; pkill -f bench2.py; pkill -f tool_call_bench.py; sleep 4

# --- preflight: restore pristine plain template (reversible) ---
echo "--- restoring pristine plain chat template (was DSML) ---" | tee -a "$LOG"
cp "$MODEL/chat_template.jinja"    "$ROOT/.bench-logs/_pre-sweep-chat_template.jinja.bak"
cp "$MODEL/tokenizer_config.json"  "$ROOT/.bench-logs/_pre-sweep-tokenizer_config.json.bak"
cp "$ORIG/chat_template.jinja"     "$MODEL/chat_template.jinja"
cp "$ORIG/tokenizer_config.json"   "$MODEL/tokenizer_config.json"
echo "template now: $(wc -l < "$MODEL/chat_template.jinja") lines (24=plain)" | tee -a "$LOG"

# --- start server (cap 2048; per-request sampling overrides drive everything) ---
: > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 2048 --temp 0.0 >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up $(date -Iseconds) ===" | tee -a "$LOG"

# --- run the sweep ---
echo "--- sweep ($PHASE) ---" | tee -a "$LOG"
cd "$ROOT"
"$BENCHPY" .bench-logs/degeneration_sweep.py "$PHASE" 2>&1 | tee -a "$LOG"

echo "=== metal::malloc in server log: $(grep -c metal::malloc "$SLOG") (want 0) ===" | tee -a "$LOG"
echo "=== sweep done $(date -Iseconds) ===" | tee -a "$LOG"

# leave server UP so the confirm phase / coherence reads reuse it without a reload.
echo "(server left running on :8765. To restore DSML tool calling afterward:" | tee -a "$LOG"
echo "   pkill -f mlx_lm.server && bash assets/deepseek-v4-dsml/install.sh )" | tee -a "$LOG"
