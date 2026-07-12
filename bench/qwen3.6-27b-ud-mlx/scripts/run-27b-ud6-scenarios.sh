#!/usr/bin/env bash
# qwen3.6-27b-ud-mlx@6bit (unsloth UD-MLX-6bit, dense 27B) — scenario throughput
# sweep. tools/local-llm-bench harness, 4 text scenarios, gen + effective t/s,
# thinking-on — directly comparable to the daily-driver's canonical scenario
# results at tools/local-llm-bench/results/qwen3.6-27b-dense-mlx-6bit/
# (creative-writing gen_tps 20.6-20.7, thinking-on, single-shot, max_tokens 2000).
#
# No no-think template patching needed — this campaign runs thinking-on throughout.
#
# Usage: bash bench/qwen3.6-27b-ud-mlx/scripts/run-27b-ud6-scenarios.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
HARNESS=$REPO/tools/local-llm-bench
LMS=/Users/vitor/.lmstudio/bin/lms
PY=python3
MODEL="qwen3.6-27b-ud-mlx@6bit"
LABEL=qwen3.6-27b-ud-mlx-6bit
CTX=65536
LOGDIR=$REPO/bench/qwen3.6-27b-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud6-scenarios-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

say "27B UD-6bit scenario sweep START (ctx $CTX, parallel 4, thinking-on)"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tail -2 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

# Assert thinking is ON before spending the sweep.
RT=$(curl -s http://127.0.0.1:1234/v1/chat/completions -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 17*23? Think step by step.\"}],\"max_tokens\":200,\"temperature\":0}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("completion_tokens_details",{}).get("reasoning_tokens",0))')
say "reasoning_tokens on probe = $RT"
if [ "${RT:-0}" -lt 1 ]; then
  say "ABORT: thinking is OFF (reasoning_tokens=$RT). Not running."
  exit 1
fi

cd "$HARNESS" || { say "ABORT: harness dir missing"; exit 1; }
for sc in creative-writing doc-summary ops-agent prefill-test; do
  say "scenario: $sc"
  "$PY" bench.py \
    --backend lmstudio \
    --scenario "scenarios/$sc.json" \
    --model "$MODEL" \
    --model-label "$LABEL" 2>&1 | tee -a "$DRIVER"
  say "scenario $sc rc=${PIPESTATUS[0]}"
done

say "27B UD-6bit scenario sweep COMPLETE — results under tools/local-llm-bench/results/$LABEL/"
