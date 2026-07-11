#!/usr/bin/env bash
# Qwen3.5-122B-A10B full quality ladder + Terminal-Bench, THINKING ON, detached.
# Sole-model (122B already resident, ctx 65k). Runs the decision-gate benches
# first (fast signal), Terminal-Bench last (longest leg).
#
# Usage: nohup setsid bash run-122b-full-ladder.sh > /dev/null 2>&1 &
#
# THINKING ON = we deliberately do NOT export BENCH_NOTHINK_PREFILL.
# BENCH_TIMEOUT=3600 bounds any single wedged/spiralling request (raised cap).
# Each leg logs to its own file; STATUS file is machine-readable for polling.
set -u

MODEL="qwen3.5-122b-a10b-mtp"
TOOLS="/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb"
REPO="/Users/vitor/LocalProjects/local-llms"
CAMP="$REPO/.claude/worktrees/bench+qwen3.5-122b-a10b/bench/qwen3.5-122b-a10b"
LOGDIR="$CAMP/logs"
STATUS="$LOGDIR/driver-status.txt"
DRIVER_LOG="$LOGDIR/driver.log"
mkdir -p "$LOGDIR"

source "$TOOLS/.venv/bin/activate"
export BENCH_TIMEOUT=3600
unset BENCH_NOTHINK_PREFILL   # thinking ON
cd "$TOOLS"

stamp() { date -Iseconds; }
log()   { echo "=== $(stamp) === $*" >> "$DRIVER_LOG"; }
set_status() { echo "$(stamp)|$*" >> "$STATUS"; }

echo "=== DRIVER START $(stamp) (thinking ON, model=$MODEL) ===" >> "$DRIVER_LOG"
set_status "DRIVER_START model=$MODEL"

# ---- run one bench2.py leg: name subcommand extra-args... ----
run_bench2() {
  local name="$1"; shift
  local leglog="$LOGDIR/${name}.log"
  set_status "RUNNING ${name}"
  log "start ${name} -> ${leglog}"
  python3 scripts/bench2.py "$@" --model "$MODEL" --max-tokens 65536 \
    > "$leglog" 2>&1
  local rc=$?
  log "done ${name} rc=${rc}"
  set_status "DONE ${name} rc=${rc}"
  sleep 10
  return $rc
}

# ---- Quality ladder (decision gate), thinking ON ----
run_bench2 humaneval    humaneval    --examples 100
run_bench2 mmlu         mmlu         --examples 100
run_bench2 drop         drop         --examples 100
run_bench2 math         math         --examples 100
run_bench2 livecodebench livecodebench --examples 50 --lcb-version release_v6

set_status "QUALITY_LADDER_COMPLETE"
log "quality ladder complete — starting Terminal-Bench"

# ---- Terminal-Bench 2.0, terminus-2 agent, thinking ON ----
TB_LOG="$LOGDIR/terminal-bench.log"
set_status "RUNNING terminal-bench"
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
cd "$REPO"
mkdir -p bench/terminal-bench/logs/tbench-runs
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/${MODEL}" \
  --env docker \
  -n 1 -y --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name qwen3.5-122b-a10b \
  > "$TB_LOG" 2>&1
TB_RC=$?
log "terminal-bench done rc=${TB_RC}"
set_status "DONE terminal-bench rc=${TB_RC}"

echo "=== DRIVER DONE $(stamp) ===" >> "$DRIVER_LOG"
set_status "ALL_DONE"
