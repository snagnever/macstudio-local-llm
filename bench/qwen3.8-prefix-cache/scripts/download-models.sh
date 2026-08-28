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
MTPLX_REVISION="123db8bcc7101455b00d9aad36c0e760c6e7de02"
MTPLX_QUALITY_REVISION="09f71b39a75c416be3c974840b53f9fbe9aa1841"
MTPLX_QUALITY_FP16_REVISION="4b3533770e01217f9b523f337b4597fd4ca50eea"
OQ4E_REVISION="c41ed507f1b16320942a1e9ce340e71d2692dee2"
DFLASH2_REVISION="dedf8df68adfb1afeaf7b7480c0a0243108177b4"
MLX_DIR="$MODEL_ROOT/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-$MLX_REVISION"
GGUF_DIR="$MODEL_ROOT/unsloth-Qwen3.8-27B-GGUF-$GGUF_REVISION"
OQ8E_DIR="$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-mtp-$OQ8E_REVISION"
OQ8E_FP16_DIR="$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-fp16-mtp-$OQ8E_FP16_REVISION"
MTPLX_DIR="$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-$MTPLX_REVISION"
MTPLX_QUALITY_DIR="$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Quality-$MTPLX_QUALITY_REVISION"
MTPLX_QUALITY_FP16_DIR="$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Quality-FP16-$MTPLX_QUALITY_FP16_REVISION"
OQ4E_DIR="$MODEL_ROOT/gcoli-Qwen3.8-27B-oQ4e-mtp-$OQ4E_REVISION"
DFLASH2_DIR="$MODEL_ROOT/incoai-Qwen3.8-27B-DFlash2-$DFLASH2_REVISION"
MANIFEST="$ROOT/bench/qwen3.8-prefix-cache/results/artifacts.json"

case "$MODE" in
  smoke|all|oq8e|mtplx|mtplx-quality|oq4e-dflash) ;;
  *)
    echo "usage: $0 {smoke|all|oq8e|mtplx|mtplx-quality|oq4e-dflash} [--print]" >&2
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

if [[ "$MODE" == "mtplx" ]]; then
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
    --revision "$MTPLX_REVISION" \
    --local-dir "$MTPLX_DIR"
  exit 0
fi

if [[ "$MODE" == "mtplx-quality" ]]; then
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality \
    --revision "$MTPLX_QUALITY_REVISION" \
    --local-dir "$MTPLX_QUALITY_DIR"
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality-FP16 \
    --revision "$MTPLX_QUALITY_FP16_REVISION" \
    --local-dir "$MTPLX_QUALITY_FP16_DIR"
  exit 0
fi

if [[ "$MODE" == "oq4e-dflash" ]]; then
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    gcoli/Qwen3.8-27B-oQ4e-mtp \
    --revision "$OQ4E_REVISION" \
    --local-dir "$OQ4E_DIR"
  run_command "$UVX_BIN" --from huggingface_hub hf download \
    incoai/Qwen3.8-27B-DFlash2 \
    --revision "$DFLASH2_REVISION" \
    --local-dir "$DFLASH2_DIR"
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
