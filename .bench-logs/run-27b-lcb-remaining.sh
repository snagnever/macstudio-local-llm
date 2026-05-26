#!/usr/bin/env bash
# Autonomous 27b LCB driver — runs all remaining batches sequentially,
# fully detached from any controlling terminal. Resumes from Q19.
#
# Usage: nohup setsid bash run-27b-lcb-remaining.sh > /dev/null 2>&1 &
#
# Each batch writes its own JSONL; merge at end.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source $REPO/.venv/bin/activate
export BENCH_TIMEOUT=3600
cd $REPO/tools/local-llm-bench-m4-32gb

LOGDIR=$REPO/.bench-logs
DRIVER_LOG="$LOGDIR/lcb-phase1-27b-driver.log"
echo "=== Driver start $(date -Iseconds) ===" >> "$DRIVER_LOG"

# Batches of 3 questions to stay well under the silent-death threshold.
# Q19-50 = 32 questions, in 11 batches.
BATCHES=(
  "19,20,21"
  "22,23,24"
  "25,26,27"
  "28,29,30"
  "31,32,33"
  "34,35,36"
  "37,38,39"
  "40,41,42"
  "43,44,45"
  "46,47,48"
  "49,50"
)

for i in "${!BATCHES[@]}"; do
  ONLY="${BATCHES[$i]}"
  BATCHLOG="$LOGDIR/lcb-phase1-27b-driver-batch$(printf %02d $((i+4))).log"
  echo "=== $(date -Iseconds) === starting batch $((i+4)) — Q$ONLY" >> "$DRIVER_LOG"
  python3 scripts/bench2.py livecodebench \
    --examples 50 --lcb-version release_v6 \
    --model "qwen3.6-27b" --max-tokens 65536 \
    --only "$ONLY" \
    > "$BATCHLOG" 2>&1
  RC=$?
  echo "=== $(date -Iseconds) === batch $((i+4)) finished rc=$RC" >> "$DRIVER_LOG"
  # tiny pause to let LM Studio breathe
  sleep 10
done

echo "=== Driver done $(date -Iseconds) ===" >> "$DRIVER_LOG"
