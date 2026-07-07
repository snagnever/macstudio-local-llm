#!/usr/bin/env bash
# Terminal-Bench 2.0 (89 tasks) — agents-a1-xl-mlx (leonsarmiento/Agents-A1-6bit-XL-mlx).
# Qwen3.5 MoE, heavy thinker → expect ~18-30h + many AgentTimeoutErrors (cf. 27b: 18h54m).
# Mirrors bench/terminal-bench/scripts/run-tbench-qwen-27b.sh. --agent-timeout-multiplier 0.5 per prior legs.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

mkdir -p bench/terminal-bench/logs/tbench-runs
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/bench/terminal-bench/logs
DRIVER_LOG="$LOGDIR/tbench-agents-a1-xl-driver.log"
RUN_LOG="$LOGDIR/tbench-agents-a1-xl.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/agents-a1-xl-mlx" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name agents-a1-xl \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
