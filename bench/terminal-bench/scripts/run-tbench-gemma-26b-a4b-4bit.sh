#!/usr/bin/env bash
# Phase B leg 2: gemma-4-26b-a4b-it-mlx@4bit on Terminal-Bench 2.0 (89 tasks).
# Quant A/B vs Phase A leg 2 (@6bit). Expected ~10 h per plan.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd $REPO

mkdir -p bench/terminal-bench/logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/bench/terminal-bench/logs
DRIVER_LOG="$LOGDIR/tbench-gemma-26b-a4b-4bit-driver.log"
RUN_LOG="$LOGDIR/tbench-gemma-26b-a4b-4bit.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/gemma-4-26b-a4b-it-mlx@4bit" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name gemma-26b-a4b-4bit \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
