#!/usr/bin/env bash
# Resume of run-27b-ud6-cheapsignals.sh — jdhodges (95.0%) and veerman (83.3%)
# already completed cleanly in the prior run; this picks up at HumanEval + MMLU
# only, skipping the ~15 min of redundant tool-calling reruns.
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
MODEL=qwen3.6-27b-ud-mlx@6bit
LOGDIR=$REPO/bench/qwen3.6-27b-ud-mlx/logs
DRIVER=$LOGDIR/ud6-cheapsignals-resume-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }

say "3/4 HumanEval (100)"
"$PY" scripts/bench2.py humaneval --model "$MODEL" --examples 100 2>&1 | tee -a "$DRIVER"
say "humaneval rc=${PIPESTATUS[0]}"

say "4/4 MMLU (100)"
"$PY" scripts/bench2.py mmlu --model "$MODEL" --examples 100 2>&1 | tee -a "$DRIVER"
say "mmlu rc=${PIPESTATUS[0]}"

say "Phase 2 cheap signals RESUME COMPLETE"
