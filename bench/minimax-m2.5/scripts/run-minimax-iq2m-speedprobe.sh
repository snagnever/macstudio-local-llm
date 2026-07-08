#!/usr/bin/env bash
# MiniMax-M2.5 UD-IQ2_M — clean speed probe (sustained gen + prefill, macmon telemetry).
# Loads sole-model at the T-Bench operating ctx (61,440 = 60k, IQ2_M's safe ceiling) so the
# numbers reflect T-Bench serving conditions. speed_probe.py runs 3 short probes (trivial /
# knowledge / code) at temp 0 and writes results + macmon jsonl to results/speed_probe/.
#
# Usage: bash bench/minimax-m2.5/scripts/run-minimax-iq2m-speedprobe.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL=minimax-m2.5@iq2_m
CTX=61440
LOGDIR=$REPO/bench/minimax-m2.5/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/iq2m-speedprobe-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export LMSTUDIO_URL=http://127.0.0.1:1234/v1

say "IQ2_M speed probe START (ctx $CTX)"
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

# leave the model RESIDENT at $CTX — T-Bench will reuse it (do not unload here)
say "IQ2_M speed probe COMPLETE — model left resident at ctx $CTX for T-Bench"
