#!/usr/bin/env bash
# Phase 3 #10 — DeepSeek V4 Flash tool-call jdhodges rerun (patched runtime).
# Pattern: nohup ... & disown (this rig lacks setsid).
#
# Usage: nohup bash .bench-logs/run-deepseek-v4-flash-toolcall-jdhodges.sh > /dev/null 2>&1 & disown
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

LOGDIR="$REPO/.bench-logs"
DRIVER_LOG="$LOGDIR/toolcall-jdhodges-deepseek-v4-flash-patched-v2-driver.log"
RUN_LOG="$LOGDIR/toolcall-jdhodges-deepseek-v4-flash-patched-v2.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

MODEL_PATH="/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"

cd "$REPO/tools/local-llm-bench-m4-32gb"
/Users/vitor/LocalProjects/local-llms/.venv/bin/python scripts/tool_call_bench.py \
  --model "$MODEL_PATH" \
  --suite jdhodges \
  --base-url http://127.0.0.1:8765/v1 \
  --force \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
