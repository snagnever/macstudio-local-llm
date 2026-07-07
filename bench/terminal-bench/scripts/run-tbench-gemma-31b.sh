#!/usr/bin/env bash
# Phase B leg 4: gemma-4-31b-it-mlx (8-bit dense) on Terminal-Bench 2.0 (89 tasks).
# Phase 2 demote candidate — abort early if rank holds. Expected ~24h per plan.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd $REPO

mkdir -p bench/terminal-bench/logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/bench/terminal-bench/logs
DRIVER_LOG="$LOGDIR/tbench-gemma-31b-driver.log"
RUN_LOG="$LOGDIR/tbench-gemma-31b.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/gemma-4-31b-it-mlx" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name gemma-31b \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
