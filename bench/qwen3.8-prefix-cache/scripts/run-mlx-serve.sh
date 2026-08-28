#!/usr/bin/env bash
set -euo pipefail

ARM="${1:-}"
MODE="${2:-}"
MLX_BIN="${QWEN38_MLX_SERVE_BIN:-mlx-serve}"
MODEL_REVISION="011e38296b3d2aa99245ed49a700459c4ac246b6"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
MODEL="${QWEN38_MLX_MODEL_DIR:-$MODEL_ROOT/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-$MODEL_REVISION}"
CTX_SIZE="${QWEN38_CTX_SIZE:-65536}"

case "$ARM" in
  A|B|C) ;;
  *)
    echo "usage: $0 {A|B|C} [--print]" >&2
    exit 64
    ;;
esac

COMMAND=(
  "$MLX_BIN"
  --model "$MODEL"
  --serve
  --host 0.0.0.0
  --port 11234
  --ctx-size "$CTX_SIZE"
  --metrics
)

case "$ARM" in
  A)
    COMMAND+=(--prefix-cache-entries 0 --no-mtp --no-pld)
    ;;
  B)
    COMMAND+=(--no-mtp --no-pld)
    ;;
  C)
    # Canonical model/runtime defaults: cache, PLD, MTP and auto depth.
    ;;
esac

if [[ "$MODE" == "--print" ]]; then
  printf '%q ' "${COMMAND[@]}"
  printf '\n'
  exit 0
fi

if [[ -n "$MODE" ]]; then
  echo "unknown option: $MODE" >&2
  exit 64
fi

if [[ ! -f "$MODEL/config.json" || ! -f "$MODEL/model.safetensors.index.json" ]]; then
  echo "pinned MLX snapshot is missing or incomplete: $MODEL" >&2
  exit 66
fi

exec "${COMMAND[@]}"
