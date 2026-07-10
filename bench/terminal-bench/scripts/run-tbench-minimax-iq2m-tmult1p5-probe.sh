#!/usr/bin/env bash
# ── RUN THIS ON THE MBP (Docker host), NOT the rig. Detached + caffeinate. ──
# FOLLOW-UP probe: is the "throughput wall" hard, or just slightly-too-tight at 1.0x?
#
# The 1.0x probe recovered 3/12 timeout fails; the rest still timed out. This re-runs ONLY the
# smallest-budget (15-min declared) tasks that timed out at 1.0x, now at --agent-timeout-multiplier
# 1.5 (= 22.5 min each). Temperature is held at 1.0 (same as the 1.0x probe) so the ONLY changed
# variable is budget: any new recovery here is purely the extra 50% time.
#   - If tasks flip to PASS → the wall was soft; 1.0x was just barely too tight.
#   - If they still time out → the wall is hard; these are genuinely throughput-bound on this box.
# Fresh job dir; does NOT touch the canonical 25.8% run or the 1.0x probe.
#
# Subset = 6 tasks (15-min budget, timed out at 1.0x). count-dataset-tokens excluded (finished-wrong,
# not a timeout → more time is irrelevant). regex-log included as a control (it LOOPED at 1.0x — we
# expect more time won't help a spinning agent; this confirms it).
#
# Launch (detached, survives the harness reaper):
#   ( nohup bash bench/terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1p5-probe.sh >/dev/null 2>&1 & disown )
set -u

RIG=http://macstudio.local:1234/v1
MODEL=minimax-m2.5@iq2_m
REPO="$HOME/LocalProjects/macstudio-local-llm"
JOBNAME=minimax-m2.5-iq2m-tmult1p5-probe

export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

cd "$REPO" || { echo "ABORT: bad REPO"; exit 1; }
TBLOG="$REPO/bench/terminal-bench/logs/tbench-${JOBNAME}.log"
: > "$TBLOG"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$TBLOG"; }

# 6 smallest-budget tasks that timed out at 1.0x
TASKS=(
  polyglot-rust-c
  polyglot-c-py
  write-compressor
  adaptive-rejection-sampler
  gpt2-codegolf
  regex-log
)

say "pre-flight: reach $MODEL at $RIG"
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { say "ABORT: $MODEL not reachable — is iq2_m still loaded on the rig? (don't run the q3_k_xl probe yet)"; exit 1; }

say "pruning Docker before run (reclaim VM pressure)"
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
docker system prune -af >/dev/null 2>&1

INCLUDE=()
for t in "${TASKS[@]}"; do INCLUDE+=( -i "terminal-bench/$t" ); done

say "Terminal-Bench 1.5x probe START — ${#TASKS[@]} tasks @ agent-timeout-multiplier 1.5 (22.5 min each), temp 1.0"
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
    tot=n1+n0+sum(exc.values())
    print(f"=== 1.5x PROBE DONE: recovered PASS={n1}/{tot}  reward0={n0}  exceptions={exc} ===")
    if rs.get('1.0'): print("  newly recovered @1.5x:", ", ".join(sorted(t.split('__')[0] for t in rs['1.0'])))
except Exception as ex:
    print("score parse failed:", ex)
PY
say "1.5x PROBE COMPLETE — results in bench/terminal-bench/logs/tbench-runs/$JOBNAME/"
