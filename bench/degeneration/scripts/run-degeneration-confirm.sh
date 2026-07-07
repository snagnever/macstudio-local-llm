#!/bin/bash
# Confirmation + ablation phase for the degeneration mitigation finding.
# Server must already be up on :8765 with the XTC fix + plain template (left by
# run-xtc-rerun.sh). Runs the winner + ablations across all 5 prompts (3 loop-prone
# + 2 normal-coherence) x 2 seeds.
# Usage: nohup bash bench/degeneration/scripts/run-degeneration-confirm.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
BENCHPY=$ROOT/.venv/bin/python
MODEL=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
LOG=$ROOT/bench/degeneration/logs/degeneration-confirm.log
BASE=http://127.0.0.1:8765/v1
export BASE MODEL
export SURVIVORS="combo_xtc_presence,combo_xtc_freq,abl_noxtc,abl_nominp,abl_presence0.5,abl_temp0.6,abl_xtc_th0.05,abl_presence_only"
export SEEDS="0,1"
export OUT="$ROOT/bench/degeneration/results/degeneration-confirm.jsonl"

: > "$LOG"
echo "=== confirm/ablation phase start $(date -Iseconds) ===" | tee -a "$LOG"
curl -sf -m 5 "$BASE/models" >/dev/null 2>&1 || { echo "SERVER NOT UP — abort" | tee -a "$LOG"; exit 1; }
cd "$ROOT"
"$BENCHPY" bench/degeneration/scripts/degeneration_sweep.py confirm 2>&1 | tee -a "$LOG"
echo "=== confirm done $(date -Iseconds) ===" | tee -a "$LOG"
