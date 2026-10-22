#!/usr/bin/env bash
# Tool-call probe of test 1 (mlx-serve #912): one server start of <arm> at 65536, then the 20-turn tool_loop.py
# protocol twice, with frequency_penalty 0 and 1 (Crush sends 1), vendor thinking sampling.
# Output: results/toolcall/<arm>-fp0.jsonl and <arm>-fp1.jsonl; each record has "correct". Both runs always run.
# usage: toolcall-probe.sh <arm> [--print]
set -euo pipefail
ARM="${1:?usage: $0 <arm> [--print]}"; shift
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/results/toolcall"
TL="$REPO/bench/qwen3.8-prefix-cache/scripts/tool_loop.py"
run_fp() {  # run_fp <penalty>
  echo "python3 '$TL' --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --runtime $ARM --runtime-revision \"\$(date -u +%F)\" --model-revision n/a --arm $ARM --session-id $ARM-fp$1-\$(date -u +%s) --output '$OUT/$ARM-fp$1.jsonl' --turns 20 --temperature 1.0 --top-p 0.95 --top-k 20 --reasoning-effort xhigh --frequency-penalty $1"
}
EXEC="mkdir -p '$OUT' && rm -f '$OUT/$ARM-fp0.jsonl' '$OUT/$ARM-fp1.jsonl' && { $(run_fp 0); $(run_fp 1); }"
exec bash "$HERE/scripts/run-arm.sh" "$ARM" 65536 --tag toolcall --exec "$EXEC" "$@"
