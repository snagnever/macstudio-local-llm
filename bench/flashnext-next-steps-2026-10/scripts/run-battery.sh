#!/usr/bin/env bash
# Quality battery of the Swift campaign (bench/swift15-flashnext-2026-10/scripts/ab-battery.sh) for any arm,
# one server start, results in this campaign: results/<subdir>/<profile>/<arm>/<suite>.jsonl.
# With --loops it then runs the loop-rate battery of bench/degeneration (degeneration_sweep.py, config
# vendor_t1_xhigh, 8 seeds, prompts exec_pt, story_en, list_en, qa_fact) into results/loops/<subdir>-<arm>.jsonl.
# usage: run-battery.sh <arm> <subdir> [--suites "humaneval gpqa livecodebench if jdhodges veerman"]
#                       [--profiles t1] [--effort xhigh] [--ctx 131072] [--label NAME] [--loops] [--print]
#   --suites none skips ab-battery (only --loops). --label names the output folder instead of the arm
#   (e.g. w1-medium for the effort sweep), so summarize_ab.py can compare two runs of the same arm.
set -euo pipefail
ARM="${1:?usage: $0 <arm> <subdir> [options]}"; SUBDIR="${2:?subdir}"; shift 2
SUITES="humaneval gpqa livecodebench if jdhodges veerman"; PROFILES=t1; EFFORT=xhigh; CTX=131072; LABEL=""; LOOPS=""; PRINT=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --suites) SUITES="$2"; shift 2 ;;
    --profiles) PROFILES="$2"; shift 2 ;;
    --effort) EFFORT="$2"; shift 2 ;;
    --ctx) CTX="$2"; shift 2 ;;
    --label) LABEL="$2"; shift 2 ;;
    --loops) LOOPS=1; shift ;;
    --print) PRINT=(--print); shift ;;
    *) echo "unknown option: $1" >&2; exit 64 ;;
  esac
done
[[ "$SUBDIR" =~ ^[a-z0-9-]+$ ]] || { echo "run-battery: subdir must be [a-z0-9-]: $SUBDIR" >&2; exit 64; }
HERE="${BATTERY_CAMPAIGN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO="$(cd "$HERE/../.." && pwd)"
BATTERY="$REPO/bench/swift15-flashnext-2026-10/scripts/ab-battery.sh"
SWEEP="$REPO/bench/degeneration/scripts/degeneration_sweep.py"
LABEL="${LABEL:-$ARM}"
LOOPS_OUT="$HERE/results/loops/$SUBDIR-$LABEL.jsonl"
export AB_ARM="$LABEL" AB_PROFILES="$PROFILES" AB_SUITES="$SUITES" AB_EFFORT="$EFFORT" \
  AB_RESULTS="$HERE/results" AB_OUT_SUBDIR="$SUBDIR"
EXEC=""
[[ "$SUITES" != none ]] && EXEC="bash '$BATTERY'"
if [[ -n "$LOOPS" ]]; then
  L="mkdir -p '$HERE/results/loops' && BASE=\"\$BASE_URL\" MODEL=\"\$MODEL_ID\" MAXTOK=16384 SEEDS=0,1,2,3,4,5,6,7"
  L+=" ONLY=vendor_t1_xhigh PROMPTS_ONLY=exec_pt,story_en,list_en,qa_fact OUT='$LOOPS_OUT' python3 '$SWEEP' screen"
  # The battery's exit code must survive the loop run: keep the worse of the two.
  if [[ -n "$EXEC" ]]; then EXEC="rc=0; $EXEC || rc=\$?; $L || rc=\$?; exit \$rc"; else EXEC="$L"; fi
fi
[[ -n "$EXEC" ]] || { echo "run-battery: nothing to run (--suites none without --loops)" >&2; exit 64; }
# bash 3.2 (the rig's): an empty array under set -u needs the ${arr[@]+...} form.
exec bash "$HERE/scripts/run-arm.sh" "$ARM" "$CTX" --tag "q-$SUBDIR-$LABEL" --exec "$EXEC" ${PRINT[@]+"${PRINT[@]}"}
