#!/usr/bin/env bash
# Refusal probe of one arm: one server start at 32768, then refusal_probe.py on the AdvBench and JBB prompt sets, and
# the Etapa U probe of the 2026-09 driver (results/etapa-u-<set>-<arm>.jsonl).
# The prompt files are logs/datasets/advbench.csv and logs/datasets/jbb.csv (not tracked; see plan Task 1).
# Verdicts go to results/refusal-<arm>-<set>.jsonl; prompts and answers only to logs/refusal-<arm>-<set>-raw.jsonl.
# usage: refusal-arm.sh <arm> [--print]
set -euo pipefail
ARM="${1:?usage: $0 <arm> [--print]}"; shift
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=(); [[ "${1:-}" == --print ]] && PASS=(--print)
DATA="$HERE/logs/datasets"
if [[ ${#PASS[@]} -eq 0 ]]; then
  for s in advbench jbb; do [[ -s "$DATA/$s.csv" ]] || { echo "refusal-arm: missing $DATA/$s.csv" >&2; exit 66; }; done
fi
# run-candidate.sh attaches memory samples to results/<arm>-<ctx>-t1.0-refusal.jsonl after the command: create it.
EXEC="touch '$HERE/results/$ARM-32768-t1.0-refusal.jsonl' && rc=0; for s in advbench jbb; do"
EXEC+=" python3 '$HERE/scripts/refusal_probe.py' --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --set \$s"
EXEC+=" --prompts '$DATA'/\$s.csv --arm $ARM --out-jsonl '$HERE/results'/refusal-$ARM-\$s.jsonl"
EXEC+=" --raw-jsonl '$HERE/logs'/refusal-$ARM-\$s-raw.jsonl || rc=\$?; done;"
# The Etapa U probe of the 2026-09 driver (50 legit prompts for over-refusal, 24 harmful ones; c1 and u1 are its history).
EXEC+=" for s in legit harmful; do python3 '$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/refusal_probe.py'"
EXEC+=" --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm $ARM --set \$s --out '$HERE/results'/etapa-u-\$s-$ARM.jsonl"
EXEC+=" || rc=\$?; done; exit \$rc"
exec bash "$HERE/scripts/run-arm.sh" "$ARM" 32768 --tag refusal --exec "$EXEC" ${PASS[@]+"${PASS[@]}"}
