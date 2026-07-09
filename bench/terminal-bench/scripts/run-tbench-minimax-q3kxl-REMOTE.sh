#!/usr/bin/env bash
# ── RUN THIS ON THE MBP (VitorMBPro2026, the Docker host), NOT the model rig. ──
# Terminal-Bench 2.0 for MiniMax-M2.5 **UD-Q3_K_XL**, model served remotely by LM Studio on the
# 128 GB rig (macstudio.local:1234). This Mac only runs Docker + the terminus-2 agent.
#
# Identical protocol to the Q3_K_S (25.8%) and IQ2_M remote runs so the delta is a clean quant
# comparison:  terminus-2 · full n=89 · --agent-timeout-multiplier 0.5 · UNPINNED rig-side sampling.
# Only the model id changes: minimax-m2.5@q3_k_xl. NOTE: q3_k_xl is served at ctx 32k (fit ceiling),
# so agent trajectories are capped at 32k — half of IQ2_M's 60k. Record >32k truncations as a floor.
#
# PREREQUISITES on this (Docker-host) Mac:
#   1. Docker Desktop running (~19.5 GB allocated — restore if it drifted down).
#   2. harbor installed:  uv tool install harbor   (NOT harbor-cli). This checkout used 0.18.0.
#   3. Same LAN as the rig; the rig must already have q3_k_xl LOADED (run the rig speed probe first):
#        curl -s http://macstudio.local:1234/api/v0/models | grep q3_k_xl   # must show state: loaded
set -u

RIG=http://macstudio.local:1234/v1          # LM Studio on the 128 GB model rig
MODEL=minimax-m2.5@q3_k_xl                   # <-- the UD-Q3_K_XL variant (served, ctx 32k, sole-model)
REPO="$HOME/LocalProjects/macstudio-local-llm"
NCONC=1                                      # concurrent trials. 1 per ~16-24 GB free Docker RAM.

export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

cd "$REPO" || { echo "ABORT: edit REPO= to this Mac's path"; exit 1; }
mkdir -p bench/terminal-bench/logs/tbench-runs
TBLOG="$REPO/bench/terminal-bench/logs/tbench-minimax-q3kxl-remote.log"

# pre-flight: model reachable AND loaded?
echo "=== pre-flight: reach the rig's model $(date -Iseconds) ==="
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { echo "ABORT: cannot reach $MODEL at $RIG — run the rig speed probe to load it first"; exit 1; }
echo "  reachable."

# clean any orphaned containers from a prior aborted run
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

echo "=== Terminal-Bench 2.0 (full 89) — remote model UD-Q3_K_XL, n-concurrent=$NCONC $(date -Iseconds) ==="
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL" \
  --env docker \
  -n "$NCONC" \
  -y \
  --quiet \
  --agent-timeout-multiplier 0.5 \
  --environment-build-timeout-multiplier 3.0 \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name minimax-m2.5-q3kxl-remote \
  > "$TBLOG" 2>&1
RC=$?
echo "=== Terminal-Bench finished rc=$RC $(date -Iseconds) ==="
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
echo "=== done. results in bench/terminal-bench/logs/tbench-runs/minimax-m2.5-q3kxl-remote/ ==="
