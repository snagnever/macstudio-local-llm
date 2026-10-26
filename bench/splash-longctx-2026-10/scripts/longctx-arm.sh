#!/usr/bin/env bash
# Long-context probe of one arm: one server start at <server-ctx>, then longctx_probe.py at each band, smallest
# first. A server above 262144 runs YaRN, which also changes the smaller bands, so each band is measured on the
# server of its column. Output: results/longctx/<arm>-<server-ctx>-<band>.jsonl.
# usage: longctx-arm.sh <arm> <server-ctx> <band> [<band> ...] [--yarn F] [--print]
set -euo pipefail
ARM="${1:?usage: $0 <arm> <server-ctx> <band> [...] [--yarn F] [--print]}"; CTX="${2:?server-ctx}"; shift 2
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BANDS=(); PASS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yarn) PASS+=(--yarn "$2"); shift 2 ;;
    --print) PASS+=(--print); shift ;;
    *) [[ "$1" =~ ^[0-9]+$ && "$1" -le "$CTX" ]] || { echo "longctx-arm: bad band $1" >&2; exit 64; }; BANDS+=("$1"); shift ;;
  esac
done
[[ ${#BANDS[@]} -gt 0 ]] || { echo "longctx-arm: no band" >&2; exit 64; }
OUT="$HERE/results/longctx"
# run-candidate.sh attaches memory samples to results/<arm>-<ctx>-t1.0-lc-q.jsonl after the command: create it.
EXEC="mkdir -p '$OUT' && touch '$HERE/results/$ARM-$CTX-t1.0-lc-q.jsonl' && rc=0; for b in ${BANDS[*]}; do"
EXEC+=" python3 '$HERE/scripts/longctx_probe.py' --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --context \$b"
EXEC+=" --arm $ARM --output \"$OUT/$ARM-$CTX-\$b.jsonl\" || rc=\$?; done; exit \$rc"
exec bash "$HERE/scripts/run-arm.sh" "$ARM" "$CTX" --tag lc-q --exec "$EXEC" ${PASS[@]+"${PASS[@]}"}
