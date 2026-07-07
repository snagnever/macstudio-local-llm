#!/usr/bin/env bash
# Phase 3 #10 — DeepSeek V4 Flash MATH (n=100, --max-tokens 65536).
# Pattern: nohup ... & disown (this rig lacks setsid).
#
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-deepseek-v4-flash-math.sh > /dev/null 2>&1 & disown
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

LOGDIR="$REPO/bench/deepseek-v4-flash/logs"
DRIVER_LOG="$LOGDIR/math-deepseek-v4-flash-driver.log"
RUN_LOG="$LOGDIR/math-deepseek-v4-flash.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

export LMSTUDIO_URL=http://127.0.0.1:8765/v1
export BENCH_TIMEOUT=3600
MODEL_PATH="/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"

cd "$REPO/tools/local-llm-bench-m4-32gb"
/Users/vitor/LocalProjects/local-llms/.venv/bin/python scripts/bench2.py math \
  --examples 100 \
  --model "$MODEL_PATH" \
  --max-tokens 65536 \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
