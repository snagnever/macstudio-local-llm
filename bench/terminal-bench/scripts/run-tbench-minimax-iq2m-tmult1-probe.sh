#!/usr/bin/env bash
# ── RUN THIS ON THE MBP (Docker host), NOT the rig. Detached + caffeinate. ──
# DIAGNOSTIC probe: how much of IQ2_M's 25.8% (23/89) T-Bench score was pure timeout-starvation?
#
# The canonical IQ2_M run used --agent-timeout-multiplier 0.5 and logged 46 AgentTimeoutErrors.
# Vendor MiniMax-M2.5 reports Terminal-Bench 2 = 51.7 (= 46/89) at FULL agent budget. This re-runs
# a curated 12-task subset of those timeout fails at --agent-timeout-multiplier 1.0 (full budget) to
# isolate the timeout variable. It does NOT touch the canonical job dir — fresh job, separate score.
# Caveat: vendor also used full-precision weights (we're 2-bit) and MiniMax's own agent scaffold
# (we use terminus-2), so recovery here measures the budget effect only, not the whole 25.8→51.7 gap.
#
# Also pins sampling temperature=1.0 (MiniMax's recommended/vendor setting). NOTE: the canonical
# 25.8% run sent NO temperature (terminus-2 leaves it unset → LM Studio server default), so this
# probe changes TWO variables vs canonical: full agent budget AND temp=1.0. Both move toward vendor
# conditions; report the recovery as a combined "match-vendor" effect, not budget alone.
#
# Subset = 12 winnable code/data/algorithm tasks (monster >60-min builds deliberately excluded).
# Launch (detached, survives the harness reaper):
#   ( nohup bash bench/terminal-bench/scripts/run-tbench-minimax-iq2m-tmult1-probe.sh >/dev/null 2>&1 & disown )
set -u

RIG=http://macstudio.local:1234/v1
MODEL=minimax-m2.5@iq2_m
REPO="$HOME/LocalProjects/macstudio-local-llm"
JOBNAME=minimax-m2.5-iq2m-tmult1-probe

export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

cd "$REPO" || { echo "ABORT: bad REPO"; exit 1; }
TBLOG="$REPO/bench/terminal-bench/logs/tbench-${JOBNAME}.log"
: > "$TBLOG"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$TBLOG"; }

# the 12 curated timeout-failed tasks (names, not task-ids; -i matches task name)
TASKS=(
  fix-code-vulnerability
  mcmc-sampling-stan
  rstan-to-pystan
  adaptive-rejection-sampler
  gpt2-codegolf
  regex-log
  count-dataset-tokens
  multi-source-data-merger
  polyglot-c-py
  polyglot-rust-c
  schemelike-metacircular-eval
  write-compressor
)

# pre-flight: rig serving the model, loaded?
say "pre-flight: reach $MODEL at $RIG"
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { say "ABORT: $MODEL not reachable — is iq2_m still loaded on the rig? (don't run the q3_k_xl probe yet)"; exit 1; }

# clean slate for the VM (avoid the wedge that hit the first run)
say "pruning Docker before run (reclaim VM pressure)"
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
docker system prune -af >/dev/null 2>&1

# build -i args (task names are dataset-prefixed: terminal-bench/<name>)
INCLUDE=()
for t in "${TASKS[@]}"; do INCLUDE+=( -i "terminal-bench/$t" ); done

say "Terminal-Bench probe START — ${#TASKS[@]} tasks @ agent-timeout-multiplier 1.0, temperature 1.0"
caffeinate -i -s harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL" \
  --agent-kwarg temperature=1.0 \
  --env docker \
  -n 1 \
  -y \
  --quiet \
  --agent-timeout-multiplier 1.0 \
  --environment-build-timeout-multiplier 3.0 \
  "${INCLUDE[@]}" \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name "$JOBNAME" \
  >> "$TBLOG" 2>&1
RC=$?
say "harbor run finished rc=$RC"
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

# score the probe
python3 - "$REPO/bench/terminal-bench/logs/tbench-runs/$JOBNAME/result.json" <<'PY' 2>&1 | tee -a "$TBLOG"
import json,sys
try:
    ev=list(json.load(open(sys.argv[1]))['stats']['evals'].values())[0]
    rs=ev['reward_stats']['reward']
    n1=len(rs.get('1.0',[])); n0=len(rs.get('0.0',[]))
    exc={k:len(v) for k,v in ev.get('exception_stats',{}).items()}
    total=n1+n0+sum(exc.values())
    rate=n1/total if total else 0.0
    proj=(23+46*rate)/89*100
    print(f"=== PROBE DONE: recovered PASS={n1}/{total}  (rate={rate*100:.0f}%)  reward0={n0}  exceptions={exc} ===")
    print(f"=== If this rate held across all 46 timeout fails: projected full score ~= {proj:.1f}% "
          f"(vs 25.8% at multiplier 0.5; vendor 51.7%) ===")
except Exception as e:
    print("score parse failed:", e)
PY
say "PROBE COMPLETE — results in bench/terminal-bench/logs/tbench-runs/$JOBNAME/"
