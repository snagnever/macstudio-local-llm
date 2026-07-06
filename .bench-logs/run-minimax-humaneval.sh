#!/usr/bin/env bash
set -u
LOG=/tmp/minimax_humaneval.log
exec > "$LOG" 2>&1
echo "=== MiniMax HumanEval driver start $(date -Iseconds) ==="

REPO=/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
LMS=/Users/vitor/.lmstudio/bin/lms
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
export BENCH_TIMEOUT=3600

# --- ensure sole-model MiniMax, ctx 32768 ---
echo "=== loading unsloth/minimax-m2.5 (sole-model, ctx 32768) $(date -Iseconds) ==="
"$LMS" unload --all 2>/dev/null
"$LMS" load unsloth/minimax-m2.5 --context-length 32768 --gpu max --parallel 1 --ttl 21600 -y
"$LMS" ps

# --- HumanEval 100 @ 32768 ---
cd "$REPO" || { echo "ABORT: repo dir missing"; exit 1; }
echo "=== HumanEval(100) start $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py humaneval --examples 100 \
  --model unsloth/minimax-m2.5 --max-tokens 32768
RC=$?
echo "=== HumanEval finished rc=$RC $(date -Iseconds) ==="

# --- CRITICAL: free the rig before the 01:00 DeepSeek LCB job ---
echo "=== unloading MiniMax $(date -Iseconds) ==="
"$LMS" unload --all 2>/dev/null
"$LMS" ps
echo "=== MINIMAX HUMANEVAL DRIVER COMPLETE rc=$RC $(date -Iseconds) ==="
