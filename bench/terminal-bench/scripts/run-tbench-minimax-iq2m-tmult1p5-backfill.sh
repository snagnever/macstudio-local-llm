#!/usr/bin/env bash
# ── RUN THIS ON THE MBP (Docker host), NOT the rig. Detached + caffeinate. ──
# BACKFILL: re-run the 2 tasks from the 1.5x probe that got infra-noise verdicts, not clean
# model verdicts, due to the mid-probe Docker daemon freeze/force-kill:
#   - polyglot-rust-c  → RuntimeError (container teardown hit "Docker daemon not responding")
#   - regex-log        → EnvironmentStartTimeoutError (env never started, model never got a shot)
# Same settings as the 1.5x probe (agent-timeout-multiplier 1.5, temperature 1.0) — only variable
# changed is a healthy Docker daemon this time. Fresh job dir; does not touch the probe job.
#
# Launch (detached, survives the harness reaper):
#   ( nohup bash bench/terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-backfill.sh >/dev/null 2>&1 & disown )
set -u

RIG=http://macstudio.local:1234/v1
MODEL=minimax-m2.5@iq2_m
REPO="$HOME/LocalProjects/macstudio-local-llm"
JOBNAME=minimax-m2.5-iq2m-tmult1p5-backfill

export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

cd "$REPO" || { echo "ABORT: bad REPO"; exit 1; }
TBLOG="$REPO/bench/terminal-bench/logs/tbench-${JOBNAME}.log"
: > "$TBLOG"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$TBLOG"; }

TASKS=( polyglot-rust-c regex-log )

say "pre-flight: reach $MODEL at $RIG"
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { say "ABORT: $MODEL not reachable — is iq2_m still loaded on the rig?"; exit 1; }

say "pre-flight: Docker daemon healthy?"
docker info >/dev/null 2>&1 || { say "ABORT: Docker daemon not responding"; exit 1; }

say "pruning Docker before run"
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
docker system prune -af >/dev/null 2>&1

INCLUDE=()
for t in "${TASKS[@]}"; do INCLUDE+=( -i "terminal-bench/$t" ); done

say "Backfill START — ${#TASKS[@]} tasks @ agent-timeout-multiplier 1.5, temp 1.0"
caffeinate -i -s harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL" \
  --agent-kwarg temperature=1.0 \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 1.5 \
  --environment-build-timeout-multiplier 3.0 \
  "${INCLUDE[@]}" \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name "$JOBNAME" \
  >> "$TBLOG" 2>&1
RC=$?
say "harbor run finished rc=$RC"
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

python3 - "$REPO/bench/terminal-bench/logs/tbench-runs/$JOBNAME/result.json" <<'PY' 2>&1 | tee -a "$TBLOG"
import json,sys
try:
    e=list(json.load(open(sys.argv[1]))['stats']['evals'].values())[0]
    rs=e['reward_stats']['reward']
    n1=len(rs.get('1.0',[])); n0=len(rs.get('0.0',[]))
    exc={k:len(v) for k,v in e.get('exception_stats',{}).items()}
    print(f"=== BACKFILL DONE: PASS={n1}  reward0={n0}  exceptions={exc} ===")
    if rs.get('1.0'): print("  ✅ passed:", ", ".join(sorted(t.split('__')[0] for t in rs['1.0'])))
    if rs.get('0.0'): print("  ❌ wrong:", ", ".join(sorted(t.split('__')[0] for t in rs['0.0'])))
except Exception as ex:
    print("score parse failed:", ex)
PY
say "BACKFILL COMPLETE — results in bench/terminal-bench/logs/tbench-runs/$JOBNAME/"
