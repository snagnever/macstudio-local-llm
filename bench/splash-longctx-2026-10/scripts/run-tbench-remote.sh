#!/usr/bin/env bash
# Run on the laptop (Docker host): Terminal-Bench 2.1 with terminus-2 against one arm served by the rig
# (hold-arm.sh there, or the daily driver for w1z). Profile t1 of run-tbench-flashnext.sh, timeouts at 1.0x
# (leaderboard rule), image builds at 3.0x (amd64 under emulation). caffeinate keeps the laptop awake.
# A stopped job resumes with: harbor job resume -p bench/splash-longctx-2026-10/logs/tbench-runs/tb21-<arm>
# usage: run-tbench-remote.sh <arm> <base-url> [--print]   (TBENCH_MODEL_ID skips the /models lookup)
set -euo pipefail
ARM="${1:?usage: $0 <arm> <base-url> [--print]}"; BASE="${2:?base-url}"; PRINT="${3:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
JOBS="bench/splash-longctx-2026-10/logs/tbench-runs"
MODEL_ID="${TBENCH_MODEL_ID:-}"
if [[ -z "$MODEL_ID" ]]; then
  MODEL_ID="$(curl -fsS --max-time 10 "$BASE/models" | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["id"])')" \
    || { echo "run-tbench-remote: cannot reach $BASE/models" >&2; exit 69; }
fi
CMD=(caffeinate -i harbor run
  --dataset terminal-bench/terminal-bench-2-1 --agent terminus-2 --model "openai/$MODEL_ID"
  --env docker -n 1 -y --quiet
  --agent-timeout-multiplier 1.0 --environment-build-timeout-multiplier 3.0
  --ak reasoning_effort=xhigh --ak temperature=1.0 --ak interleaved_thinking=true
  --ak 'llm_call_kwargs={"top_p":0.95,"extra_body":{"top_k":20,"min_p":0,"presence_penalty":0,"repetition_penalty":1.0}}'
  --jobs-dir "$JOBS" --job-name "tb21-$ARM")
if [[ "$PRINT" == --print ]]; then echo "${CMD[*]}"; exit 0; fi
cd "$REPO"; mkdir -p "$JOBS"
export OPENAI_API_BASE="$BASE" OPENAI_API_KEY=local DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
docker info >/dev/null 2>&1 || { echo "run-tbench-remote: Docker is not running" >&2; exit 69; }
echo "=== start $(date -Iseconds) arm=$ARM model=$MODEL_ID base=$BASE ==="
rc=0; "${CMD[@]}" || rc=$?
echo "=== done $(date -Iseconds) rc=$rc ==="
exit $rc
