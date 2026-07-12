#!/usr/bin/env bash
# qwen3.6-27b-mtp — clean speed probe (sustained gen + prefill, macmon telemetry).
# First bench of the MTP (multi-token-prediction, arch qwen35) build of qwen3.6-27b.
# Loads sole-model at ctx 65,000 (the ctx it arrived staged at) with --parallel 1 so the
# numbers are a clean single-stream measurement, comparable to the 2026-05-17 baseline
# probe of plain qwen3.6-27b (results/speed_probe/qwen3.6-27b_20260517_172229_results.json).
# speed_probe.py runs 3 short probes (trivial / knowledge / code) at temp 0 and writes
# results + macmon jsonl to results/speed_probe/.
#
# Usage: bash bench/qwen3.6-mtp/scripts/run-qwen36-mtp-speedprobe.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL=qwen3.6-27b-mtp
CTX=65000
LOGDIR=$REPO/bench/qwen3.6-mtp/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/mtp-speedprobe-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export LMSTUDIO_URL=http://127.0.0.1:1234/v1

say "qwen3.6-27b-mtp speed probe START (ctx $CTX)"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 1 --ttl 172800 -y 2>&1 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

# confirm the served id (the probe needs it exact)
say "served models:"
curl -s http://127.0.0.1:1234/v1/models 2>/dev/null | tr ',' '\n' | grep -i '"id"' | tee -a "$DRIVER"

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }
say "running speed_probe.py"
"$PY" scripts/speed_probe.py "$MODEL" results/speed_probe 2>&1 | tee -a "$DRIVER"
say "speed probe rc=${PIPESTATUS[0]}"

# leave the model RESIDENT at $CTX for the follow-up benches (do not unload here)
say "qwen3.6-27b-mtp speed probe COMPLETE — model left resident at ctx $CTX"
