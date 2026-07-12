#!/usr/bin/env bash
# MTP draft-depth sweep — does a deeper Draft MTP window widen the structured-output
# win, or does falling acceptance eat it? Same GGUF, Draft MTP ON, only
# --speculative-draft-max-tokens varied. Anchors already measured in Phase 3:
#   OFF  -> results/q36-mtp-off   ;   max=2 -> results/q36-mtp-on
# This adds max in {4,6,8}. Everything else fixed (ctx 65000, GPU max, parallel 4).
#
# Requires the BENCH_NOTHINK_PREFILL patch in bench.py (env-gated no-think).
#
# Usage: bash bench/qwen3.6-mtp/scripts/run-mtp-draftdepth-sweep.sh [MODEL_KEY] [DEPTHS...]
#   default MODEL_KEY=qwen3.6-35b-a3b-mtp  DEPTHS="4 6 8"
set -u

REPO=/Users/vitor/LocalProjects/local-llms
HARNESS=$REPO/tools/local-llm-bench
LMS=/Users/vitor/.lmstudio/bin/lms
PY=python3
KEY=${1:-qwen3.6-35b-a3b-mtp}; shift || true
TAG=$(echo "$KEY" | grep -oiE '27b|35b|[0-9]+b' | head -1); TAG=${TAG:-model}
DEPTHS=${*:-4 6 8}
CTX=65000
LOGDIR=$REPO/bench/qwen3.6-mtp/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/mtp-draftdepth-${KEY}-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export BENCH_NOTHINK_PREFILL=1
export LMSTUDIO_URL=http://127.0.0.1:1234/v1

say "MTP draft-depth sweep START for $KEY (depths: $DEPTHS)"
for d in $DEPTHS; do
  id="q36-${TAG}-draft${d}"
  say "DEPTH=$d : unload all, load $KEY as id=$id (--speculative-draft-max-tokens $d)"
  "$LMS" unload --all 2>/dev/null
  "$LMS" load "$KEY" --identifier "$id" --context-length $CTX --gpu max --parallel 4 --ttl 3600 \
      --speculative-draft-mtp --speculative-draft-max-tokens "$d" --speculative-draft-min-tokens 0 \
      -y 2>&1 | tee -a "$DRIVER"
  "$LMS" ps 2>&1 | tee -a "$DRIVER"

  cd "$HARNESS" || { say "ABORT: harness dir missing"; exit 1; }
  for sc in creative-writing doc-summary ops-agent prefill-test; do
    say "DEPTH=$d scenario: $sc"
    "$PY" bench.py --backend lmstudio --scenario "scenarios/$sc.json" \
        --model "$id" --model-label "$id" 2>&1 | tee -a "$DRIVER"
    say "DEPTH=$d scenario $sc rc=${PIPESTATUS[0]}"
  done
done
say "MTP draft-depth sweep COMPLETE — results in tools/local-llm-bench/results/q36-draft{$DEPTHS}"
