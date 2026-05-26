#!/usr/bin/env bash
# Phase B leg 5: qwen3.6-27b (6-bit dense) on Terminal-Bench 2.0 (89 tasks).
# Knowledge king, dense thinking — longest leg. CONDITIONAL on F1 guard
# passing in leg 3 (35b-a3b > 5%). Expected ~30+h per plan.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd $REPO

mkdir -p .bench-logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/.bench-logs
DRIVER_LOG="$LOGDIR/tbench-qwen-27b-driver.log"
RUN_LOG="$LOGDIR/tbench-qwen-27b.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/qwen3.6-27b" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir .bench-logs/tbench-runs \
  --job-name qwen-27b \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
