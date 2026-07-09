#!/usr/bin/env bash
# ── RUN THIS ON THE MBP, DETACHED. Retries the 16 EnvironmentStartTimeoutError trials. ──
# The IQ2_M run's 16 env-start failures were a Docker LinuxKit VM wedge (root-caused: NOT sleep —
# caffeinate held the whole window; see plan-iq2m-envfail-retry.md). This attacks the VM wedge,
# then resumes only the failed trials, and auto-recovers if the VM re-wedges (up to 3 rounds).
#
# Launch (detached, survives the harness reaper):
#   ( nohup bash bench/terminal-bench/scripts/retry-tbench-minimax-iq2m-envfail.sh >/dev/null 2>&1 & disown )
set -u

REPO="$HOME/LocalProjects/macstudio-local-llm"
cd "$REPO" || exit 1
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"
export OPENAI_API_BASE="http://macstudio.local:1234/v1"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64

JOB="$REPO/bench/terminal-bench/logs/tbench-runs/minimax-m2.5-iq2m-remote"
LOG="$REPO/bench/terminal-bench/logs/iq2m-envfail-retry.log"
MODEL=minimax-m2.5@iq2_m
MAXROUNDS=3
: > "$LOG"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$LOG"; }

# count remaining EnvironmentStartTimeoutError trials in the job
env_fail_count(){
  python3 - "$JOB/result.json" <<'PY' 2>/dev/null
import json,sys
try:
    ev=list(json.load(open(sys.argv[1]))['stats']['evals'].values())[0]
    print(len(ev.get('exception_stats',{}).get('EnvironmentStartTimeoutError',[])))
except Exception:
    print(-1)
PY
}

docker_healthy(){ docker info >/dev/null 2>&1; }

restart_docker(){
  say "restarting Docker Desktop"
  osascript -e 'quit app "Docker"' 2>/dev/null
  # wait for it to actually exit
  for i in $(seq 1 30); do pgrep -xq "Docker Desktop" || pgrep -xq "Docker" || break; sleep 2; done
  open -a Docker
  say "waiting for Docker daemon to come healthy"
  for i in $(seq 1 90); do docker_healthy && { say "Docker healthy"; return 0; }; sleep 4; done
  say "WARN: Docker did not report healthy after ~6 min; proceeding anyway"
}

# pre-flight: rig model must be loaded (retry reuses iq2_m)
curl -s --max-time 10 "$OPENAI_API_BASE/models" 2>/dev/null | grep -q "$MODEL" \
  || { say "ABORT: $MODEL not served on rig — is it still loaded?"; exit 1; }

start=$(env_fail_count)
say "retry START — $start EnvironmentStartTimeoutError trials to recover (job: $JOB)"

round=0
while [ "$round" -lt "$MAXROUNDS" ]; do
  round=$((round+1))
  say "ROUND $round/$MAXROUNDS — pruning stale Docker images (reclaim VM pressure)"
  docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
  docker system prune -af >/dev/null 2>&1
  restart_docker

  say "ROUND $round — harbor job resume (filter EnvironmentStartTimeoutError)"
  caffeinate -i -s harbor job resume -p "$JOB" -f EnvironmentStartTimeoutError -y >> "$LOG" 2>&1
  rc=$?
  say "ROUND $round — resume returned rc=$rc"

  remaining=$(env_fail_count)
  say "ROUND $round — EnvironmentStartTimeoutError remaining: $remaining"
  [ "$remaining" = "0" ] && { say "all env-start failures recovered"; break; }
  say "ROUND $round — $remaining still env-failed (VM re-wedged) — looping"
done

# final score
python3 - "$JOB/result.json" <<'PY' 2>&1 | tee -a "$LOG"
import json,sys
ev=list(json.load(open(sys.argv[1]))['stats']['evals'].values())[0]
rs=ev['reward_stats']['reward']
n1=len(rs.get('1.0',[])); n0=len(rs.get('0.0',[]))
exc={k:len(v) for k,v in ev.get('exception_stats',{}).items()}
print(f"=== RETRY DONE: PASS={n1}  official={n1}/89={100*n1/89:.1f}%  (graded {n1}/{n1+n0}={100*n1/(n1+n0):.1f}%)  exceptions={exc} ===")
PY
say "RETRY SCRIPT COMPLETE"
