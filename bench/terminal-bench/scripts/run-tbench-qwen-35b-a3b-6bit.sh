#!/usr/bin/env bash
# Phase B leg 3: qwen3.6-35b-a3b@6bit on Terminal-Bench 2.0 (89 tasks).
# F1 THINKING-FORMAT GUARD: if this score ≤ 5% → thinking-format incompatible with
# T-Bench on this rig; ABORT the 27b run (saves ~30h). Expected ~14h per plan.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd $REPO

mkdir -p bench/terminal-bench/logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/bench/terminal-bench/logs
DRIVER_LOG="$LOGDIR/tbench-qwen-35b-a3b-6bit-driver.log"
RUN_LOG="$LOGDIR/tbench-qwen-35b-a3b-6bit.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/qwen3.6-35b-a3b@6bit" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name qwen-35b-a3b-6bit \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
