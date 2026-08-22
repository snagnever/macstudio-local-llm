#!/usr/bin/env bash
# MiniMax-M2.5 UD-IQ2_M — complete context-vs-speed sweep (the piece the 3-question probe
# doesn't cover): reload at each ctx in {1024..65536}, measure decode t/s + peak RAM/swap.
# Answers "how far does decode fall as context fills?" — we saw ~43 t/s shallow (probe/HE)
# vs ~26-33 t/s deep (LCB spirals); this quantifies the curve.
#
# The upstream context_speed_bench.py hardcodes MODEL_KEY + output name, so we patch a BACKUP
# copy (never git-touch the submodule — a sibling session shares it) and restore after.
# Ends by RE-STAGING IQ2_M at 60k for the pending remote Terminal-Bench.
#
# Usage: nohup bash bench/minimax-m2.5/scripts/run-minimax-iq2m-ctxspeed.sh >/dev/null 2>&1 & disown
set -u

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=${REPO_DIR:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}
BENCH=${BENCH_DIR:-$REPO/tools/local-llm-bench-m4-32gb}
PY=${PYTHON_BIN:-$REPO/.venv/bin/python}
LMS=${LMS_BIN:-lms}
SCRIPT=$BENCH/scripts/context_speed_bench.py
LOGDIR=$REPO/bench/minimax-m2.5/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/iq2m-ctxspeed-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

say "IQ2_M context-speed sweep START"

# --- patch a backup copy: MODEL_KEY -> IQ2_M, output name model-specific (no git) ---
cp "$SCRIPT" "$SCRIPT.iq2mbak"
sed -i '' 's#^MODEL_KEY = .*#MODEL_KEY = "minimax-m2.5@iq2_m"#' "$SCRIPT"
sed -i '' 's#context_speed_bench\.json#context_speed_bench_minimax-m2.5-iq2m.json#' "$SCRIPT"
say "patched MODEL_KEY=minimax-m2.5@iq2_m; grep check:"
grep -nE '^MODEL_KEY|context_speed_bench_minimax' "$SCRIPT" | tee -a "$DRIVER"

# --- run the sweep (it manages its own load/unload per ctx via the LM Studio API) ---
cd "$BENCH" || { say "ABORT: bench dir missing"; mv "$SCRIPT.iq2mbak" "$SCRIPT"; exit 1; }
say "running context_speed_bench.py (sizes 1024..65536)"
"$PY" scripts/context_speed_bench.py >> "$DRIVER" 2>&1
RC=$?
say "sweep rc=$RC"

# --- restore the untouched submodule script (no git) ---
mv "$SCRIPT.iq2mbak" "$SCRIPT"
say "submodule script restored"

# --- re-stage IQ2_M at 60k, long TTL, for the pending remote Terminal-Bench ---
say "re-staging IQ2_M at ctx 61440 for T-Bench"
"$LMS" unload --all 2>/dev/null
"$LMS" load minimax-m2.5@iq2_m --context-length 61440 --gpu max --parallel 1 --ttl 172800 -y 2>&1 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"
say "IQ2_M context-speed sweep COMPLETE — model re-staged at 60k, ready for T-Bench"
