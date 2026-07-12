#!/usr/bin/env bash
# MTP A/B — isolate what LM Studio's Draft MTP speculative decoding actually buys.
#
# The earlier sweeps compared GGUF-vs-MLX, which conflates quant+format with MTP.
# This instead loads the SAME GGUF twice — Draft MTP OFF then ON — everything else
# identical (ctx 65000, GPU max, parallel 4, draft max-tokens 2, matching the
# user's LM Studio Load config) and runs the 4-scenario throughput sweep each way.
# The OFF→ON delta is the pure MTP effect.
#
# Requires the BENCH_NOTHINK_PREFILL patch in bench.py (env-gated no-think).
#
# Usage: bash bench/qwen3.6-mtp/scripts/run-mtp-ab-toggle.sh [MODEL_KEY]
#   default MODEL_KEY=qwen3.6-35b-a3b-mtp
set -u

REPO=/Users/vitor/LocalProjects/local-llms
HARNESS=$REPO/tools/local-llm-bench
LMS=/Users/vitor/.lmstudio/bin/lms
PY=python3
KEY=${1:-qwen3.6-35b-a3b-mtp}
TAG=$(echo "$KEY" | grep -oiE '27b|35b|[0-9]+b' | head -1); TAG=${TAG:-model}
CTX=65000
DRAFT_MAX=2
LOGDIR=$REPO/bench/qwen3.6-mtp/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/mtp-ab-${KEY}-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export BENCH_NOTHINK_PREFILL=1
export LMSTUDIO_URL=http://127.0.0.1:1234/v1

run_arm() {
  local arm="$1"; shift          # "off" | "on"
  local id="q36-${TAG}-mtp-${arm}"   # API identifier -> distinct result dir (model-tagged)
  say "ARM=$arm : unload all, load $KEY as id=$id ($*)"
  "$LMS" unload --all 2>/dev/null
  "$LMS" load "$KEY" --identifier "$id" --context-length $CTX --gpu max --parallel 4 \
      --ttl 3600 "$@" -y 2>&1 | tee -a "$DRIVER"
  "$LMS" ps 2>&1 | tee -a "$DRIVER"

  cd "$HARNESS" || { say "ABORT: harness dir missing"; exit 1; }
  for sc in creative-writing doc-summary ops-agent prefill-test; do
    say "ARM=$arm scenario: $sc"
    "$PY" bench.py --backend lmstudio --scenario "scenarios/$sc.json" \
        --model "$id" --model-label "$id" 2>&1 | tee -a "$DRIVER"
    say "ARM=$arm scenario $sc rc=${PIPESTATUS[0]}"
  done
}

say "MTP A/B START for $KEY (ctx $CTX, parallel 4, gpu max, draft-max $DRAFT_MAX)"
run_arm off --no-speculative-draft-mtp
run_arm on  --speculative-draft-mtp --speculative-draft-max-tokens $DRAFT_MAX --speculative-draft-min-tokens 0
say "MTP A/B COMPLETE — results in tools/local-llm-bench/results/q36-${TAG}-mtp-off and .../q36-${TAG}-mtp-on"
