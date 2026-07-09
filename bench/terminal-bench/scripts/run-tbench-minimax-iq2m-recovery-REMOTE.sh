#!/usr/bin/env bash
# ── RUN THIS ON THE DOCKER-HOST MAC, same machine as run-tbench-minimax-iq2m-REMOTE.sh. ──
# Hand-off: waits for the main IQ2_M remote T-Bench run to finish, then reruns ONLY the
# genuine verifier-fails (tasks the agent finished within budget but scored wrong) at the
# vendor-recommended sampling (temperature=1.0, per the MiniMax HF card) to check whether
# unpinned/off-spec sampling caused a fixable miss.
#
# AgentTimeoutError tasks are deliberately EXCLUDED: a temperature change can't rescue a
# budget-exhausted trial, and on this always-thinking model a hotter temperature can lengthen
# reasoning traces rather than shorten them — retrying those would just burn hours for a
# near-zero chance of flipping the result.
#
# This is a SEPARATE, clearly-labeled recovery leg (job-name minimax-m2.5-iq2m-remote-recovery)
# — same pattern as the LCB ceiling-recovery runs. Do not blend its results into the primary
# T-Bench score; none of the other 7 rig models got this treatment, so it isn't a fair
# apples-to-apples number. Report it alongside the main score as "N of M genuine-fails
# recovered at temp=1.0."
set -u

REPO="$HOME/LocalProjects/macstudio-local-llm"
RIG=http://macstudio.local:1234/v1
MODEL=minimax-m2.5@iq2_m
MAIN_JOB="$REPO/bench/terminal-bench/logs/tbench-runs/minimax-m2.5-iq2m-remote"
RECOVERY_JOB_NAME=minimax-m2.5-iq2m-remote-recovery
LOG="$REPO/bench/terminal-bench/logs/tbench-minimax-iq2m-recovery-handoff.log"

mkdir -p "$REPO/bench/terminal-bench/logs"
exec > "$LOG" 2>&1
echo "=== recovery hand-off armed $(date -Iseconds) ==="

export PATH="$HOME/.local/bin:$PATH"

echo "=== waiting for main run's harbor process to exit... ==="
while pgrep -f "harbor run .*--job-name $(basename "$MAIN_JOB") " >/dev/null 2>&1; do
  sleep 60
done
echo "=== main run process exited $(date -Iseconds) ==="

TASKS=$(python3 - "$MAIN_JOB" <<'PY'
import json, sys
J = sys.argv[1]
r = json.load(open(J + "/result.json"))
ev = list(r["stats"]["evals"].values())[0]
fails = set(t.rsplit("__", 1)[0] for t in ev["reward_stats"]["reward"].get("0.0", []))
timeouts = set(t.rsplit("__", 1)[0] for t in ev.get("exception_stats", {}).get("AgentTimeoutError", []))
genuine = sorted(fails - timeouts)
print("\n".join(genuine))
PY
)

if [ -z "$TASKS" ]; then
  echo "=== no genuine verifier-fails found in the finished run — nothing to recover; exiting ==="
  exit 0
fi

N=$(echo "$TASKS" | grep -c .)
echo "=== genuine verifier-fail tasks to retry at temperature=1.0 (n=$N): ==="
echo "$TASKS"

INCLUDE_ARGS=()
while IFS= read -r t; do
  [ -n "$t" ] && INCLUDE_ARGS+=(-i "$t")
done <<< "$TASKS"

echo "=== pre-flight: reach the rig's model $(date -Iseconds) ==="
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { echo "ABORT: cannot reach $MODEL at $RIG"; exit 1; }
echo "  reachable."

docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
cd "$REPO" || { echo "ABORT: repo missing"; exit 1; }
mkdir -p bench/terminal-bench/logs/tbench-runs

echo "=== starting recovery run: $N task(s), temperature=1.0 $(date -Iseconds) ==="
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL" \
  --ak temperature=1.0 \
  --env docker \
  "${INCLUDE_ARGS[@]}" \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --environment-build-timeout-multiplier 3.0 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name "$RECOVERY_JOB_NAME"
RC=$?
echo "=== recovery run finished rc=$RC $(date -Iseconds) ==="
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
echo "=== done. results in bench/terminal-bench/logs/tbench-runs/$RECOVERY_JOB_NAME/ ==="
