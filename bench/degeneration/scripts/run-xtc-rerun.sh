#!/bin/bash
# Re-run ONLY the XTC configs after fixing the xtc_special_tokens ragged-list bug
# in mlx_lm/server.py. Plain template is already restored by the screen runner.
# Usage: nohup bash bench/degeneration/scripts/run-xtc-rerun.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
PY=$ROOT/venvs/mlx-v4-flash/bin/python
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
SLOG=$ROOT/bench/degeneration/logs/server-degeneration.log
LOG=$ROOT/bench/degeneration/logs/degeneration-xtc.log
BASE=http://127.0.0.1:8765/v1
export BASE MODEL
export ONLY="xtc_p0.5_th0.1,xtc_p0.5_th0.1_minp,xtc_p1.0_th0.1_minp,xtc_p0.5_th0.2_minp,combo_xtc_presence,combo_xtc_freq"
export OUT="$ROOT/bench/degeneration/results/degeneration-xtc.jsonl"

: > "$LOG"
echo "=== XTC re-run start $(date -Iseconds) ===" | tee -a "$LOG"
pkill -f mlx_lm.server; pkill -f bench2.py; sleep 4

: > "$SLOG"
nohup "$PY" -m mlx_lm.server --model "$MODEL" --host 0.0.0.0 --port 8765 \
  --max-tokens 2048 --temp 0.0 >> "$SLOG" 2>&1 & disown
for i in $(seq 1 120); do curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 && break; sleep 2; done
curl -sS -m 600 "$BASE/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" >/dev/null 2>&1
echo "=== server up (XTC fix loaded) $(date -Iseconds) ===" | tee -a "$LOG"

cd "$ROOT"
"$BENCHPY" bench/degeneration/scripts/degeneration_sweep.py screen 2>&1 | tee -a "$LOG"

echo "=== metal::malloc in server log: $(grep -c metal::malloc "$SLOG") (want 0) ===" | tee -a "$LOG"
echo "=== XTC re-run done $(date -Iseconds) ===" | tee -a "$LOG"
echo "(server left up on :8765)" | tee -a "$LOG"
