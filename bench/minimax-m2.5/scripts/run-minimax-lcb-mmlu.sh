#!/usr/bin/env bash
set -u
LOG=/tmp/minimax_lcb_mmlu.log
exec > "$LOG" 2>&1
echo "=== MiniMax LCB+MMLU driver start $(date -Iseconds) ==="

REPO=/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
LMS=/Users/vitor/.lmstudio/bin/lms
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
export BENCH_TIMEOUT=3600

# --- ensure sole-model MiniMax, ctx 32768 ---
echo "=== loading unsloth/minimax-m2.5 (sole-model, ctx 32768) $(date -Iseconds) ==="
"$LMS" unload --all 2>/dev/null
"$LMS" load unsloth/minimax-m2.5 --context-length 32768 --gpu max --parallel 1 --ttl 43200 -y
"$LMS" ps

cd "$REPO" || { echo "ABORT: repo dir missing"; exit 1; }

# --- LiveCodeBench v6 (50) @ 32768 ---
echo "=== LCB v6 (50) start $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py livecodebench --examples 50 \
  --model unsloth/minimax-m2.5 --lcb-version release_v6 --max-tokens 32768
RC_LCB=$?
echo "=== LCB finished rc=$RC_LCB $(date -Iseconds) ==="

# --- MMLU (100) @ 32768 ---
echo "=== MMLU (100) start $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py mmlu --examples 100 \
  --model unsloth/minimax-m2.5 --max-tokens 32768
RC_MMLU=$?
echo "=== MMLU finished rc=$RC_MMLU $(date -Iseconds) ==="

# --- free the rig ---
echo "=== unloading MiniMax $(date -Iseconds) ==="
"$LMS" unload --all 2>/dev/null
"$LMS" ps
echo "=== MINIMAX LCB+MMLU DRIVER COMPLETE lcb_rc=$RC_LCB mmlu_rc=$RC_MMLU $(date -Iseconds) ==="
