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
  A|B|C|FS) ;;
  *)
    echo "usage: $0 {A|B|C|FS} [--print]" >&2
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
  FS)
    # Flash-Next (qwen4_exp) no mlx-serve >=26.8.11: MTP nativo explícito.
    COMMAND+=(--mtp)
    ;;
esac

# Knobs opcionais de memória p/ contexto máximo (evita o 400 do memory guard a 256K):
# KV quantizado encolhe o working memory; max-resident-mem 0 desliga o cap auto de 80%.
if [[ -n "${QWEN38_MLX_KV_QUANT:-}" ]]; then
  COMMAND+=(--kv-quant "$QWEN38_MLX_KV_QUANT" --kv-attn-mode "${QWEN38_MLX_KV_ATTN_MODE:-fused}")
fi
if [[ -n "${QWEN38_MLX_MAX_RESIDENT_MEM:-}" ]]; then
  COMMAND+=(--max-resident-mem "$QWEN38_MLX_MAX_RESIDENT_MEM")
fi
# Chunk de prefill menor reduz o workspace por chunk (fix documentado p/ OOM de prefill longo).
if [[ -n "${QWEN38_MLX_PREFILL_CHUNK:-}" ]]; then
  COMMAND+=(--prefill-chunk "$QWEN38_MLX_PREFILL_CHUNK")
fi

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
