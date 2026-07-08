#!/usr/bin/env bash
# MiniMax-M2.5 UD-IQ2_M — context-ceiling probe folded into LCB truncation recovery.
#
# Two questions in one pass:
#   1. Does the 64,512 `Compute error` cliff (measured on Q3_K_S) MOVE on the smaller
#      IQ2_M quant? KV cache is fp16 and quant-independent, so theory says no — but
#      IQ2_M has ~20 GB more headroom, so if the cliff were memory-bound it would rise.
#   2. Do IQ2_M's LCB truncations (32k-cap FAILs) recover with a bigger budget?
#      Q3_K_S recovered 2/5 at 60k (Q38, Q48); Q8/Q19/Q44 were real spirals.
#
# Strategy: descend from full native ctx, stepping down ONLY on a memory/compute
# error. First ctx that loads AND infers becomes the recovery budget. A non-memory
# failure HALTs (descending wouldn't fix it). 61440 (60k) is the known-good floor.
#
# Usage: nohup bash bench/minimax-m2.5/scripts/run-minimax-iq2m-ceiling-recovery.sh >/dev/null 2>&1 & disown
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
PY=$REPO/.venv/bin/python
LMS=/Users/vitor/.lmstudio/bin/lms
MODEL=minimax-m2.5@iq2_m
BASE=http://127.0.0.1:1234/v1

LOGDIR=$REPO/bench/minimax-m2.5/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/iq2m-ceiling-recovery-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

# --- 1. truncation set from the main LCB run log ---
LCBLOG=$LOGDIR/iq2m-lcb.log
TRUNC=$(grep "TRUNC" "$LCBLOG" 2>/dev/null | grep -oE 'Q[0-9]+' | grep -oE '[0-9]+' | sort -n | uniq | paste -sd, -)
say "truncation set: ${TRUNC:-none}"
if [ -z "$TRUNC" ]; then say "no truncations -> nothing to recover"; exit 0; fi

# --- 2. load at the proven recovery ctx ---
# Ceiling probe (run 2026-07-07) established: 131072 loads + passes a 1-token infer,
# 196608 fails on memory — so the load cliff is MEMORY-bound (moved from Q3_K_S's
# 64,512 up to ~128k on the 20 GB-lighter quant), NOT a fixed Metal buffer limit.
# BUT 128k is a paper ceiling: sustained generation there tips into swap pressure and
# stalls to ~0 t/s (Q8 recovery produced 0 tokens in a 30-min timeout). So recovery
# runs at 60k/57344 — the exact config Q3_K_S recovered at, and comfortably in-memory
# on the lighter IQ2_M weights. Enough budget to let a 32k-spiral conclude, no pressure.
CTX=61440
MAXTOK=57344
export BENCH_TIMEOUT=3600
say "loading $MODEL ctx=$CTX for recovery (max-tokens=$MAXTOK)"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length "$CTX" --gpu max --parallel 1 --ttl 7200 -y 2>&1 | tee -a "$DRIVER"

# --- 3. recover the truncated questions ---
cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }
say "recovery: livecodebench --examples 50 --only $TRUNC --max-tokens $MAXTOK"
"$PY" scripts/bench2.py livecodebench --examples 50 --only "$TRUNC" --model "$MODEL" \
  --lcb-version release_v6 --max-tokens "$MAXTOK" > "$LOGDIR/iq2m-lcb-recovery.log" 2>&1
say "recovery rc=$?"

"$LMS" unload --all 2>/dev/null
say "CEILING-RECOVERY COMPLETE ctx=$CTX trunc=$TRUNC"
