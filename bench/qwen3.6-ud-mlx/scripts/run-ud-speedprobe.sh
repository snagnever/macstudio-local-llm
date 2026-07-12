#!/usr/bin/env bash
# qwen3.6-35b-a3b-ud-mlx (unsloth UD-MLX-4bit) — clean 3-question speed probe.
# Phase 1a of bench/qwen3.6-ud-mlx/plan.md. Sole-model, --parallel 1 for a clean
# single-stream decode t/s number, comparable to the @6bit ~90 t/s anchor.
# speed_probe.py runs trivial/knowledge/code at temp 0 + macmon telemetry.
#
# Usage: bash bench/qwen3.6-ud-mlx/scripts/run-ud-speedprobe.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL=qwen3.6-35b-a3b-ud-mlx          # served id (speed_probe hits the API)
CTX=65536
LOGDIR=$REPO/bench/qwen3.6-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud-speedprobe-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export LMSTUDIO_URL=http://127.0.0.1:1234/v1

say "ud-mlx speed probe START (ctx $CTX, parallel 1)"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 1 --ttl 172800 -y 2>&1 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

say "served models:"
curl -s http://127.0.0.1:1234/v1/models 2>/dev/null | tr ',' '\n' | grep -i '"id"' | tee -a "$DRIVER"

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }
say "running speed_probe.py"
"$PY" scripts/speed_probe.py "$MODEL" results/speed_probe 2>&1 | tee -a "$DRIVER"
say "speed probe rc=${PIPESTATUS[0]}"

# reload at --parallel 4 for the scenario sweep (matches @6bit Load config)
say "reloading at --parallel 4 for scenario sweep"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tee -a "$DRIVER"
say "ud-mlx speed probe COMPLETE — model resident at ctx $CTX, parallel 4"
