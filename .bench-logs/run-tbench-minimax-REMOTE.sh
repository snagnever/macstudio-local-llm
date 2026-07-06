#!/usr/bin/env bash
# ── RUN THIS ON THE OTHER APPLE-SILICON MAC (the Docker host), NOT on the model rig. ──
# Terminal-Bench 2.0 for MiniMax-M2.5, with the MODEL served remotely by LM Studio on the
# 128 GB rig (192.168.68.123:1234). This Mac only runs Docker + the terminus-2 agent, so the
# 98.69 GB model and the task containers no longer fight for RAM — the fix for the NO-GO.
#
# PREREQUISITES on this (Docker-host) Mac:
#   1. Docker Desktop installed + running. Give it generous RAM (Settings → Resources):
#      as much as you can spare — task images are amd64 (Rosetta/qemu emulation) and hungry.
#   2. harbor installed:  uv tool install harbor-cli   (or however the rig got 0.8.0)
#   3. Same LAN as the rig; confirm reachability FIRST:
#        curl -s http://192.168.68.123:1234/v1/models | grep minimax   # must return the id
#   4. This script's REPO path below is local to THIS Mac — edit if different.
set -u

RIG=http://192.168.68.123:1234/v1          # LM Studio on the 128 GB model rig
MODEL=unsloth/minimax-m2.5
REPO="$HOME/LocalProjects/local-llms"      # <-- EDIT to this Mac's checkout path
NCONC=1                                     # concurrent trials. 1 per ~16-24 GB free Docker RAM.
                                            #   32 GB free → 1 ; 64 GB → 2 ; 96 GB+ → 3-4
export OPENAI_API_BASE="$RIG"
export OPENAI_API_KEY="lm-studio"
export DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

cd "$REPO" || { echo "ABORT: edit REPO= to this Mac's path"; exit 1; }
mkdir -p .bench-logs/tbench-runs
TBLOG="$REPO/.bench-logs/tbench-minimax-remote.log"

# pre-flight: model reachable?
echo "=== pre-flight: reach the rig's model $(date -Iseconds) ==="
curl -s --max-time 10 "$RIG/models" | grep -q "$MODEL" \
  || { echo "ABORT: cannot reach $MODEL at $RIG — check LAN / LM Studio bind 0.0.0.0"; exit 1; }
echo "  reachable."

# clean any orphaned containers from a prior aborted run (harbor leaves them on timeout)
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

echo "=== Terminal-Bench 2.0 (full 89) — remote model, n-concurrent=$NCONC $(date -Iseconds) ==="
harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL" \
  --env docker \
  -n "$NCONC" \
  -y \
  --quiet \
  --timeout-multiplier 1.0 \
  --environment-build-timeout 3.0 \
  --jobs-dir .bench-logs/tbench-runs \
  --job-name minimax-m2.5-remote \
  > "$TBLOG" 2>&1
RC=$?
echo "=== Terminal-Bench finished rc=$RC $(date -Iseconds) ==="
# cleanup orphans on exit
docker ps -q 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1
echo "=== done. results in .bench-logs/tbench-runs/minimax-m2.5-remote/ ==="
