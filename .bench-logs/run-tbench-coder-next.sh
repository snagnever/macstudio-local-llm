#!/usr/bin/env bash
# Phase A leg 1: qwen/qwen3-coder-next on Terminal-Bench 2.0 (89 tasks).
# Pattern copied from .bench-logs/run-27b-lcb-remaining.sh — nohup setsid → PPID=1
# to survive the 2-h Bash run_in_background silent-kill (F3).
#
# Usage: nohup setsid bash .bench-logs/run-tbench-coder-next.sh > /dev/null 2>&1 &
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd $REPO

mkdir -p .bench-logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/.bench-logs
DRIVER_LOG="$LOGDIR/tbench-coder-next-driver.log"
RUN_LOG="$LOGDIR/tbench-coder-next.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/qwen/qwen3-coder-next" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir .bench-logs/tbench-runs \
  --job-name coder-next \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
