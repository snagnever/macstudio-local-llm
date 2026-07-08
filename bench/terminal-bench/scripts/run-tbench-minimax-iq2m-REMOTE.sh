#!/usr/bin/env bash
# ── RUN THIS ON THE OTHER APPLE-SILICON MAC (the Docker host), NOT on the model rig. ──
# Terminal-Bench 2.0 for MiniMax-M2.5 **UD-IQ2_M**, model served remotely by LM Studio on the
# 128 GB rig (macstudio.local:1234). This Mac only runs Docker + the terminus-2 agent.
#
# Identical protocol to the Q3_K_S remote run (25.8%) so the delta is a clean quant comparison:
#   terminus-2 · full n=89 · --agent-timeout-multiplier 0.5 · UNPINNED rig-side sampling
#   (Q3_K_S was also unpinned — pinning official sampling is a separate future improvement).
# Only the model id changes: minimax-m2.5@iq2_m (78 GB, ~43 t/s) instead of Q3_K_S.
#
# PREREQUISITES on this (Docker-host) Mac:
#   1. Docker Desktop running, generous RAM (task images are amd64 / Rosetta-qemu, hungry).
#   2. harbor installed:  uv tool install harbor-cli   (rig used 0.8.0)
#   3. Same LAN as the rig; confirm reachability FIRST:
#        curl -s http://macstudio.local:1234/v1/models | grep iq2_m   # must return the id
#   4. Edit REPO below to THIS Mac's checkout path.
set -u

RIG=http://macstudio.local:1234/v1          # LM Studio on the 128 GB model rig
MODEL=minimax-m2.5@iq2_m                     # <-- the IQ2_M variant (served, ctx 60k, sole-model)
REPO="$HOME/LocalProjects/macstudio-local-llm"  # <-- EDIT to this Mac's checkout path
NCONC=1                                     # concurrent trials. 1 per ~16-24 GB free Docker RAM.

export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

cd "$REPO" || { echo "ABORT: edit REPO= to this Mac's path"; exit 1; }
mkdir -p bench/terminal-bench/logs/tbench-runs
TBLOG="$REPO/bench/terminal-bench/logs/tbench-minimax-iq2m-remote.log"

# pre-flight: model reachable?
echo "=== pre-flight: reach the rig's model $(date -Iseconds) ==="
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { echo "ABORT: cannot reach $MODEL at $RIG — check LAN / LM Studio bind 0.0.0.0 / model loaded"; exit 1; }
echo "  reachable."

# clean any orphaned containers from a prior aborted run
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

echo "=== Terminal-Bench 2.0 (full 89) — remote model IQ2_M, n-concurrent=$NCONC $(date -Iseconds) ==="
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
  --job-name minimax-m2.5-iq2m-remote \
  > "$TBLOG" 2>&1
RC=$?
echo "=== Terminal-Bench finished rc=$RC $(date -Iseconds) ==="
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
echo "=== done. results in bench/terminal-bench/logs/tbench-runs/minimax-m2.5-iq2m-remote/ ==="
