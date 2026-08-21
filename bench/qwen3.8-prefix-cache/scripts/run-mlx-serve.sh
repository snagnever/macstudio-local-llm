#!/usr/bin/env bash
set -euo pipefail

ARM="${1:-}"
MODE="${2:-}"
MLX_BIN="${QWEN38_MLX_SERVE_BIN:-mlx-serve}"
MODEL="${QWEN38_MLX_MODEL:-ddalcu/Qwen3.8-27B-MLX-Serve-8bit}"
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

exec "${COMMAND[@]}"
