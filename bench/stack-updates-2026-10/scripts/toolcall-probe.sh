#!/usr/bin/env bash
# Tool-call probe of test 1 (mlx-serve #912): one server start of <arm> at 65536, then 5 sessions of the
# tool_loop.py protocol with --turns 4 (one full read/search/test/record cycle each, 20 tool calls), once with
# frequency_penalty 0 and once with 1 (Crush sends 1), vendor thinking sampling. The 20-turn protocol in one
# session is not used: after the 4 tasks of its prompt the model answers in text at turn 5 on 26.10.1 too.
# Output: results/toolcall/<arm>-fp0.jsonl and <arm>-fp1.jsonl ("correct" per turn, one "verdict" per session).
# Every session always runs. A failed turn leaves its full reply in results/logs/tool-loop/ (gitignored).
# --sessions N runs N sessions per penalty (default 5). --suffix S writes <arm>-fp0-S.jsonl and tags the server
# run toolcall-S, so a second probe of the same arm keeps the first one's files. --max-tokens N caps each tool
# turn (default 512, the historical cap; Task 10 traced every turn-1 failure to it).
# usage: toolcall-probe.sh <arm> [--sessions N] [--suffix S] [--max-tokens N] [--print]
set -euo pipefail
ARM="${1:?usage: $0 <arm> [--sessions N] [--suffix S] [--max-tokens N] [--print]}"; shift
SESSIONS=5; SUFFIX=""; MAXTOK=512; PASS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sessions) SESSIONS="$2"; shift 2 ;;
    --suffix) SUFFIX="-$2"; shift 2 ;;
    --max-tokens) MAXTOK="$2"; shift 2 ;;
    *) PASS+=("$1"); shift ;;
  esac
done
[[ "$SESSIONS" =~ ^[1-9][0-9]*$ ]] || { echo "toolcall-probe: --sessions must be a positive integer" >&2; exit 64; }
# TOOLCALL_CAMPAIGN_DIR sends results and the server run to another campaign folder (it needs scripts/run-arm.sh).
HERE="${TOOLCALL_CAMPAIGN_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/results/toolcall"
TL="$REPO/bench/qwen3.8-prefix-cache/scripts/tool_loop.py"
run_fp() {  # run_fp <penalty>
  echo "python3 '$TL' --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --runtime $ARM --runtime-revision \"\$(date -u +%F)\" --model-revision n/a --arm $ARM --session-id $ARM-fp$1$SUFFIX-s\$s-\$(date -u +%s) --output '$OUT/$ARM-fp$1$SUFFIX.jsonl' --turns 4 --temperature 1.0 --top-p 0.95 --top-k 20 --reasoning-effort xhigh --frequency-penalty $1 --max-tokens $MAXTOK"
}
# run-candidate.sh attaches memory samples to results/<arm>-65536-t1.0-toolcall.jsonl after the command: create it.
EXEC="mkdir -p '$OUT' && rm -f '$OUT/$ARM-fp0$SUFFIX.jsonl' '$OUT/$ARM-fp1$SUFFIX.jsonl' && touch '$HERE/results/$ARM-65536-t1.0-toolcall$SUFFIX.jsonl'"
EXEC+=" && for s in \$(seq $SESSIONS); do $(run_fp 0); done; for s in \$(seq $SESSIONS); do $(run_fp 1); done"
exec bash "$HERE/scripts/run-arm.sh" "$ARM" 65536 --tag "toolcall$SUFFIX" --exec "$EXEC" ${PASS[@]+"${PASS[@]}"}
