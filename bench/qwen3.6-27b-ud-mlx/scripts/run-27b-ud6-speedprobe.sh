#!/usr/bin/env bash
# qwen3.6-27b-ud-mlx@6bit (unsloth UD-MLX-6bit, dense 27B) — clean speed probe.
# Phase 1 of bench/qwen3.6-27b-ud-mlx/plan.md. Sole-model, --parallel 1 for a
# clean single-stream decode t/s number, comparable to the @6bit ~90 t/s anchor.
# This is a DENSE 27B (all params/token) so expect materially lower t/s than the
# MoE 35B-A3B (3B active) — that gap is the whole point of the measurement.
#
# Usage: bash bench/qwen3.6-27b-ud-mlx/scripts/run-27b-ud6-speedprobe.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL="qwen3.6-27b-ud-mlx@6bit"       # served id (speed_probe hits the API)
CTX=65536
LOGDIR=$REPO/bench/qwen3.6-27b-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud6-speedprobe-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export LMSTUDIO_URL=http://127.0.0.1:1234/v1

say "27B UD-6bit speed probe START (ctx $CTX, parallel 1)"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 1 --ttl 172800 -y 2>&1 | tail -2 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }
say "running speed_probe.py"
"$PY" scripts/speed_probe.py "$MODEL" results/speed_probe 2>&1 | tee -a "$DRIVER"
say "speed probe rc=${PIPESTATUS[0]}"

# reload at --parallel 4 for the cheap-signals sweep (matches @6bit Load config)
say "reloading at --parallel 4 for cheap-signals sweep"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tail -2 | tee -a "$DRIVER"
say "27B UD-6bit speed probe COMPLETE — model resident at ctx $CTX, parallel 4"
