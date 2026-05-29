#!/usr/bin/env bash
# Phase 3 #10 — DeepSeek V4 Flash on Terminal-Bench 2.0 (89 tasks, 0.5x cap).
# Pattern: nohup ... & disown (this rig lacks setsid).
#
# Usage: nohup bash .bench-logs/run-tbench-deepseek-v4-flash.sh > /dev/null 2>&1 & disown
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

mkdir -p .bench-logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:8765/v1"
export OPENAI_API_KEY="not-needed"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/.bench-logs
DRIVER_LOG="$LOGDIR/tbench-deepseek-v4-flash-driver.log"
RUN_LOG="$LOGDIR/tbench-deepseek-v4-flash.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

# Note: mlx_lm.server validates model field against the loaded --model path.
# Pass the full path through LiteLLM's openai/ provider prefix.
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai//Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir .bench-logs/tbench-runs \
  --job-name deepseek-v4-flash \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
