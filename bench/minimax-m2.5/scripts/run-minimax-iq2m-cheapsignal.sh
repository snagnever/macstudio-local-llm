#!/usr/bin/env bash
# MiniMax-M2.5 UD-IQ2_M (78.2 GB, 2-bit) cheap-signal quality gate.
# Roadmap rank 2 — hard-gated: 2-bit risk per the deepseek-v4-flash-dq collapse.
# Protocol (model card): jdhodges >=85% gate -> HumanEval -> LCB, kill on gate fail.
# Sole-model rig; runs at ctx 32768 for apples-to-apples with the Q3_K_S scorecard.
#
# Usage: nohup bash bench/minimax-m2.5/scripts/run-minimax-iq2m-cheapsignal.sh >/dev/null 2>&1 & disown
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL=minimax-m2.5@iq2_m
BASE=http://127.0.0.1:1234/v1
CTX=32768
GATE=0.85

LOGDIR=$REPO/bench/minimax-m2.5/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/iq2m-cheapsignal-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

export LMSTUDIO_URL=$BASE
export BENCH_TIMEOUT=3600

say "IQ2_M cheap-signal START (ctx $CTX, gate jdhodges>=$GATE)"

# --- load sole-model ---
say "loading $MODEL sole-model ctx $CTX"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 1 --ttl 21600 -y 2>&1 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$LOGDIR/iq2m-load-ps.log" | tee -a "$DRIVER"

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }

# --- tool-calling: jdhodges (gate) + veerman ---
say "jdhodges(40)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges --base-url "$BASE" --force \
  --run-prefix toolcall > "$LOGDIR/iq2m-jdhodges.log" 2>&1
say "veerman(12)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman --base-url "$BASE" --force \
  --run-prefix toolcall > "$LOGDIR/iq2m-veerman.log" 2>&1

# --- read jdhodges score for the gate ---
SCORE=$("$PY" - <<'PYEOF'
import glob, json, os
runs = sorted(glob.glob("benchmarks/runs/toolcall_jdhodges_*iq2*summary.json"), key=os.path.getmtime)
if not runs:
    runs = sorted(glob.glob("benchmarks/runs/toolcall_jdhodges_*summary.json"), key=os.path.getmtime)
print(json.load(open(runs[-1]))["score"] if runs else "NA")
PYEOF
)
say "jdhodges score=$SCORE (gate=$GATE)"

PASS=$("$PY" -c "import sys; s='$SCORE'; print('1' if s!='NA' and float(s)>=$GATE else '0')" 2>/dev/null || echo 0)

if [ "$PASS" != "1" ]; then
  say "GATE FAILED (jdhodges $SCORE < $GATE) -> NO-GO, skipping HumanEval/LCB"
  "$LMS" unload --all 2>/dev/null
  say "IQ2_M cheap-signal COMPLETE verdict=NO-GO"
  exit 0
fi

say "GATE PASSED (jdhodges $SCORE) -> knowledge benches"

# --- HumanEval(100) ---
say "HumanEval(100)"
"$PY" scripts/bench2.py humaneval --examples 100 --model "$MODEL" --max-tokens $CTX \
  > "$LOGDIR/iq2m-humaneval.log" 2>&1
say "HumanEval rc=$?"

# --- LiveCodeBench v6 (50) ---
say "LCB v6(50)"
"$PY" scripts/bench2.py livecodebench --examples 50 --model "$MODEL" --lcb-version release_v6 --max-tokens $CTX \
  > "$LOGDIR/iq2m-lcb.log" 2>&1
say "LCB rc=$?"

# --- free the rig ---
say "unloading"
"$LMS" unload --all 2>/dev/null
"$LMS" ps 2>&1 | tee -a "$DRIVER"
say "IQ2_M cheap-signal COMPLETE verdict=GATE-PASSED (see per-bench summaries)"
