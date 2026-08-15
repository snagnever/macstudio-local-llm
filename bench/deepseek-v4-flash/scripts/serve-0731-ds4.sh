#!/usr/bin/env bash
# Serve DeepSeek-V4-Flash-0731 on the DwarfStar (ds4) Metal engine.
#
# Replaces the llama-server recipe for this model: ds4 is a dedicated C+Metal
# engine for the deepseek4 arch, so none of the llama.cpp workarounds apply
# (no --no-repack, no -np 1, no 2.24.0 pin).
#
# Usage:
#   bash bench/deepseek-v4-flash/scripts/serve-0731-ds4.sh [--dspark] [--ctx N]
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
ENGINE=$ROOT/vendor/ds4
MODELDIR=~/.lmstudio/models/antirez/deepseek-v4-gguf
M=$MODELDIR/DeepSeek-V4-Flash-Layers37-42Q4KExperts-OtherExpertLayersIQ2XXSGateUp-Q2KDown-AProjQ8-SExpQ8-OutQ8-chat-v2-imatrix-fixed-0731.gguf
MTP=$MODELDIR/DeepSeek-V4-Flash-DSpark-support-0731.gguf
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
PORT=8000
CTX=65536
SPEC=()

mkdir -p "$LOGDIR"
while [ $# -gt 0 ]; do
  case "$1" in
    --dspark) SPEC=(--mtp "$MTP" --dspark); shift ;;
    --ctx)    CTX=$2; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

say(){ echo "=== $* $(date -Iseconds) ==="; }

# --- sole-model preflight (weights are ~97.6 GB; nothing else may hold GPU memory) ---
pgrep -f mlx_lm.server >/dev/null && { say "ABORT: mlx_lm.server running"; exit 1; }
pgrep -f "llama-server" >/dev/null && { say "ABORT: llama-server running"; exit 1; }
/Users/vitor/.lmstudio/bin/lms ps 2>/dev/null | grep -q . && { say "ABORT: LM Studio has a model loaded"; exit 1; }
[ -f "$M" ] || { say "ABORT: model not found: $M"; exit 1; }

SRVLOG=$LOGDIR/0731-ds4-server.log
say "starting ds4-server ctx=$CTX dspark=${#SPEC[@]} -> $SRVLOG"
# Record the loaded path: the UD-Q2_K_XL campaign could not be reproduced because
# no artifact preserved which GGUF the server actually opened.
say "model_path=$M"
( cd "$ENGINE" && nohup ./ds4-server -m "$M" --metal -c "$CTX" \
    --host 127.0.0.1 --port "$PORT" "${SPEC[@]+"${SPEC[@]}"}" \
    > "$SRVLOG" 2>&1 & disown )

# Cold load reads ~97.6 GB off SSD; allow a generous window.
# --max-time is load-bearing: ds4-server accepts the socket before it finishes
# requesting Metal residency, so a bare `curl -sf` blocks until load completes
# instead of retrying, and the loop never ticks.
for _ in $(seq 1 180); do
  curl -sf --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break
  sleep 5
done
curl -sf --max-time 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null \
  || { say "ABORT: server not healthy — see $SRVLOG"; exit 1; }

# ds4 mmaps the weights as shared Metal buffers, so RSS/phys_footprint read ~5 GB
# and are meaningless here. The planned figure in the server log is the real one.
say "server healthy on :$PORT"
grep -E "^ds4: memory:" "$SRVLOG" | tail -1
echo "harness: LMSTUDIO_URL=http://127.0.0.1:$PORT/v1"
echo "thinking OFF -> model id 'deepseek-chat' | thinking HIGH -> 'deepseek-v4-flash'"
