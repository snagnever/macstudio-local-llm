#!/usr/bin/env bash
# qwen3.6-27b-mtp — scenario throughput sweep via the local-llm-bench harness
# (the tool behind the "Generation throughput by scenario" dashboard).
#
# Runs the 4 text scenarios (creative-writing, doc-summary, ops-agent, prefill-test)
# through tools/local-llm-bench/bench.py, which reports EFFECTIVE tok/s
# (output / total wall-clock incl. prefill) — the number you actually wait for —
# alongside raw generation tok/s. Thinking disabled to match the recorded dense
# baseline (results/qwen3.6-27b-dense-mlx-6bit/, MLX 6-bit, same rig).
#
# NO-THINK MECHANISM: this is a GGUF (Qwen3.6-27B-UD-Q6_K_XL) with no external
# chat_template.jinja for the harness's --no-think to patch, and LM Studio ignores
# request-body chat_template_kwargs. Per unsloth's docs the only switch is
# enable_thinking=false, whose template branch emits a pre-closed <think></think>.
# We reproduce that via BENCH_NOTHINK_PREFILL=1 (bench.py prefills that block as a
# trailing assistant turn on each call — env-gated, inert for other harness users).
#
# NB: baseline is MLX-6bit-dense; this build is the GGUF MTP quant. The delta
# therefore conflates the MTP head with quant+format — read it as "does the MTP
# build serve faster in practice", not a clean MTP-isolated measurement.
#
# The model must already be loaded in LM Studio (this leg leaves it resident from
# the speed probe). ctx >= 16k required; we're at 65k.
#
# Usage: bash bench/qwen3.6-mtp/scripts/run-qwen36-mtp-scenarios.sh [MODEL_ID] [LABEL]
#   defaults: MODEL_ID=qwen3.6-27b-mtp  LABEL=<MODEL_ID>
#   e.g.:     ... run-qwen36-mtp-scenarios.sh qwen3.6-35b-a3b-mtp
set -u

REPO=/Users/vitor/LocalProjects/local-llms
HARNESS=$REPO/tools/local-llm-bench
PY=python3
MODEL=${1:-qwen3.6-27b-mtp}
LABEL=${2:-$MODEL}
LOGDIR=$REPO/bench/qwen3.6-mtp/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/mtp-scenarios-${MODEL}-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export BENCH_NOTHINK_PREFILL=1
say "qwen3.6-27b-mtp scenario sweep START (backend=lmstudio, no-think via prefill)"

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

say "qwen3.6-27b-mtp scenario sweep COMPLETE — results under tools/local-llm-bench/results/$LABEL/"
