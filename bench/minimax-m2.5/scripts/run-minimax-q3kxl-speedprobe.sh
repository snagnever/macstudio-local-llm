#!/usr/bin/env bash
# ── RUN THIS ON THE RIG (macstudio.local, M4 Max 128 GB), NOT the MBP. ──
# MiniMax-M2.5 UD-Q3_K_XL — clean speed probe (sustained gen + prefill, macmon telemetry).
# Loads sole-model at the T-Bench operating ctx (32,768 = 32k). UD-Q3_K_XL is 101 GB and
# peaks ~124 GB at 32k — it does NOT fit at 60k, so 32k is the ceiling (see plan-q3kxl-tbench.md).
# speed_probe.py runs 3 short probes (trivial / knowledge / code) at temp 0 and writes
# results + macmon jsonl to results/speed_probe/. Leaves the model RESIDENT for T-Bench.
#
# Usage (on the rig): bash bench/minimax-m2.5/scripts/run-minimax-q3kxl-speedprobe.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL=minimax-m2.5@q3_k_xl
CTX=32768                      # UD-Q3_K_XL fit ceiling on 128 GB (~124 GB peak). 60k OOMs.
LOGDIR=$REPO/bench/minimax-m2.5/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/q3kxl-speedprobe-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export LMSTUDIO_URL=http://127.0.0.1:1234/v1

say "UD-Q3_K_XL speed probe START (ctx $CTX)"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 1 --ttl 172800 -y 2>&1 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

# confirm the served id (harbor/probe need it exact)
say "served models:"
curl -s http://127.0.0.1:1234/v1/models 2>/dev/null | tr ',' '\n' | grep -i '"id"' | tee -a "$DRIVER"

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }
say "running speed_probe.py"
"$PY" scripts/speed_probe.py "$MODEL" results/speed_probe 2>&1 | tee -a "$DRIVER"
say "speed probe rc=${PIPESTATUS[0]}"

# leave the model RESIDENT at $CTX — the MBP T-Bench trigger polls for this and reuses it.
say "UD-Q3_K_XL speed probe COMPLETE — model left resident at ctx $CTX for T-Bench"
