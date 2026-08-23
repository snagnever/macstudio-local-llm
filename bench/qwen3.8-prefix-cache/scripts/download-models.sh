#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MODE="${1:-}"
PRINT_MODE="${2:-}"
UVX_BIN="${QWEN38_UVX_BIN:-uvx}"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
MLX_REVISION="011e38296b3d2aa99245ed49a700459c4ac246b6"
GGUF_REVISION="4ca720788d1e01f1bff70c033e0d0028fd02e502"
OQ8E_REVISION="c99e5aad8a478f71c10b9a3dde6709158b690da6"
OQ8E_FP16_REVISION="4761782b9455f335292f4d6cb0c89570dff27a11"
MLX_DIR="$MODEL_ROOT/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-$MLX_REVISION"
GGUF_DIR="$MODEL_ROOT/unsloth-Qwen3.8-27B-GGUF-$GGUF_REVISION"
OQ8E_DIR="$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-mtp-$OQ8E_REVISION"
OQ8E_FP16_DIR="$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-fp16-mtp-$OQ8E_FP16_REVISION"
MANIFEST="$ROOT/bench/qwen3.8-prefix-cache/results/artifacts.json"

case "$MODE" in
  smoke|all|oq8e) ;;
  *)
    echo "usage: $0 {smoke|all|oq8e} [--print]" >&2
    exit 64
    ;;
esac
if [[ -n "$PRINT_MODE" && "$PRINT_MODE" != "--print" ]]; then
  echo "unknown option: $PRINT_MODE" >&2
  exit 64
fi

run_command() {
  if [[ "$PRINT_MODE" == "--print" ]]; then
    printf '%q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

if [[ "$MODE" == "oq8e" ]]; then
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    Jundot/Qwen3.8-27B-oQ8e-mtp \
    --revision "$OQ8E_REVISION" \
    --local-dir "$OQ8E_DIR"
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    Jundot/Qwen3.8-27B-oQ8e-fp16-mtp \
    --revision "$OQ8E_FP16_REVISION" \
    --local-dir "$OQ8E_FP16_DIR"
  exit 0
fi

run_command "$UVX_BIN" --from huggingface_hub hf download \
  ddalcu/Qwen3.8-27B-MLX-Serve-8bit \
  --revision "$MLX_REVISION" \
  --local-dir "$MLX_DIR"

GGUF_FILES=(
  README.md
  config.json
  Qwen3.8-27B-UD-Q4_K_XL.gguf
  MTP/mtp-Qwen3.8-27B-Q4_0.gguf
)
if [[ "$MODE" == "all" ]]; then
  GGUF_FILES+=(
    Qwen3.8-27B-UD-Q6_K_XL.gguf
    Qwen3.8-27B-UD-Q8_K_XL.gguf
  )
fi
run_command "$UVX_BIN" --from huggingface_hub hf download \
  unsloth/Qwen3.8-27B-GGUF \
  "${GGUF_FILES[@]}" \
  --revision "$GGUF_REVISION" \
  --local-dir "$GGUF_DIR"

run_command python3 "$ROOT/bench/qwen3.8-prefix-cache/scripts/artifact_manifest.py" \
  --output "$MANIFEST" \
  --mlx-dir "$MLX_DIR" \
  --mlx-revision "$MLX_REVISION" \
  --gguf-dir "$GGUF_DIR" \
  --gguf-revision "$GGUF_REVISION"
