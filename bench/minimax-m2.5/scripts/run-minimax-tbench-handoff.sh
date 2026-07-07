#!/usr/bin/env bash
# Autonomous hand-off: wait for the running LCB leg to finish, abort the pending MMLU
# (WITHOUT unloading MiniMax), then run Terminal-Bench 2.0 (full 89), then MMLU, then unload.
set -u
LOG=/tmp/minimax_tbench_handoff.log
exec > "$LOG" 2>&1
echo "=== hand-off driver armed $(date -Iseconds) ==="

REPO=/Users/vitor/LocalProjects/local-llms
BREPO=$REPO/tools/local-llm-bench-m4-32gb
LMS=/Users/vitor/.lmstudio/bin/lms
LCBLOG=/tmp/minimax_lcb_mmlu.log
MODEL=unsloth/minimax-m2.5

# --- 1. wait for LCB to finish (the LCB+MMLU driver writes this line after the LCB python returns) ---
echo "=== waiting for LCB to finish... $(date -Iseconds) ==="
until grep -qa "=== LCB finished" "$LCBLOG" 2>/dev/null; do sleep 30; done
echo "=== LCB finished detected $(date -Iseconds) ==="

# --- 2. stop the old driver so MMLU + its unload do NOT run; leave the model resident ---
pkill -f "caffeinate -i bash bench/minimax-m2.5/scripts/run-minimax-lcb-mmlu.sh" 2>/dev/null
pkill -f "run-minimax-lcb-mmlu.sh" 2>/dev/null
pkill -f "bench2.py mmlu" 2>/dev/null   # in case MMLU already started in the race window
sleep 3
echo "=== old LCB+MMLU driver stopped; model should still be resident ==="
"$LMS" ps

# --- 3. reload MiniMax at ctx 65536 (from 32768) for Terminal-Bench's long agent
#        trajectories; ~125 GB peak, safe on 128 GB (native cap is 196608). Long TTL (48h). ---
echo "=== reloading MiniMax at ctx 65536, ttl 48h $(date -Iseconds) ==="
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length 65536 --gpu max --parallel 1 --ttl 172800 -y
"$LMS" ps

# --- 3b. LCB truncation recovery: rerun ONLY the two questions that hit the 32k cap
#         (Q8 leetcode/hard 3298 = over-elaboration; Q19 atcoder/hard abc354_d = think-spiral)
#         at max-tokens 60000 now that ctx is 64k. Writes a SEPARATE summary (no auto-merge);
#         fold into the LCB score manually afterward. Cheap (2 q) and runs while 64k is fresh. ---
cd "$BREPO" || { echo "ABORT: bench repo missing"; exit 1; }
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
export BENCH_TIMEOUT=3600
echo "=== LCB recovery (Q8,Q19 @ max-tokens 60000) start $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py livecodebench --examples 50 --only 8,19 \
  --model "$MODEL" --lcb-version release_v6 --max-tokens 60000
RC_REC=$?
echo "=== LCB recovery finished rc=$RC_REC $(date -Iseconds) ==="

# --- 4. Terminal-Bench 2.0 (full 89) via harbor ---
export OPENAI_API_BASE="http://127.0.0.1:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
cd "$REPO"
mkdir -p bench/terminal-bench/logs/tbench-runs
TBLOG=$REPO/bench/minimax-m2.5/logs/tbench-minimax-m2.5.log
echo "=== Terminal-Bench 2.0 (full 89) start $(date -Iseconds) ==="
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL" \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name minimax-m2.5 \
  > "$TBLOG" 2>&1
RC_TB=$?
echo "=== Terminal-Bench finished rc=$RC_TB $(date -Iseconds) ==="

# --- 5. deferred MMLU (100), then unload ---
cd "$BREPO"
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
export BENCH_TIMEOUT=3600
echo "=== MMLU (100) start $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py mmlu --examples 100 --model "$MODEL" --max-tokens 32768
RC_MMLU=$?
echo "=== MMLU finished rc=$RC_MMLU $(date -Iseconds) ==="

echo "=== unloading MiniMax $(date -Iseconds) ==="
"$LMS" unload --all 2>/dev/null
"$LMS" ps
echo "=== MINIMAX TBENCH HAND-OFF COMPLETE lcb_recovery_rc=$RC_REC tb_rc=$RC_TB mmlu_rc=$RC_MMLU $(date -Iseconds) ==="
