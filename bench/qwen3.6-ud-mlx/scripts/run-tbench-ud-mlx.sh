#!/usr/bin/env bash
# Phase 3: qwen3.6-35b-a3b-ud-mlx (unsloth UD-MLX-4bit) on Terminal-Bench 2.0.
# Adapted from bench/terminal-bench/scripts/run-tbench-qwen-35b-a3b-6bit.sh — same
# Harbor / terminus-2 / LiteLLM chain, same 0.5x agent-timeout cap, so the score is
# directly comparable to the published @6bit 28.1% (25/64 PASS, #3 on rig).
# The @6bit F1 thinking-format guard PASSED on this exact chain, and UD shares the
# template family, so thinking-on is expected to work. Expected ~15 h.
#
# Model must be loaded thinking-on in LM Studio (ctx 65k, parallel 4).
# Usage: bash bench/qwen3.6-ud-mlx/scripts/run-tbench-ud-mlx.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
cd "$REPO"

export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

LOGDIR=$REPO/bench/qwen3.6-ud-mlx/logs
JOBSDIR=$LOGDIR/tbench-runs
mkdir -p "$JOBSDIR"
DRIVER_LOG="$LOGDIR/tbench-ud-mlx-driver.log"
RUN_LOG="$LOGDIR/tbench-ud-mlx.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

# Preflight: model reachable + thinking on (the @6bit anchor is thinking-on).
RT=$(curl -s "$OPENAI_API_BASE/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen3.6-35b-a3b-ud-mlx","messages":[{"role":"user","content":"hi, think first"}],"max_tokens":40,"temperature":0}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("completion_tokens_details",{}).get("reasoning_tokens",0))' 2>/dev/null)
echo "preflight reasoning_tokens=$RT" >> "$DRIVER_LOG"
if [ "${RT:-0}" -lt 1 ]; then
  echo "ABORT: thinking OFF (reasoning_tokens=$RT) — clean-reload the model first" >> "$DRIVER_LOG"
  exit 1
fi

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/qwen3.6-35b-a3b-ud-mlx" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir "$JOBSDIR" \
  --job-name qwen-35b-a3b-ud-mlx \
  > "$RUN_LOG" 2>&1
RC=$?
echo "=== Driver done $(date -Iseconds) rc=$RC ===" >> "$DRIVER_LOG"
