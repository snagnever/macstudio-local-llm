#!/usr/bin/env bash
set -euo pipefail

ARM="${1:-}"
MODE="${2:-}"
LLAMA_BIN="${QWEN38_LLAMA_SERVER_BIN:-llama-server}"
MODEL_REVISION="4ca720788d1e01f1bff70c033e0d0028fd02e502"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
GGUF_DIR="${QWEN38_GGUF_DIR:-$MODEL_ROOT/unsloth-Qwen3.8-27B-GGUF-$MODEL_REVISION}"
MTP_FILE="${QWEN38_GGUF_MTP_FILE:-$GGUF_DIR/MTP/mtp-Qwen3.8-27B-Q4_0.gguf}"
CTX_SIZE="${QWEN38_CTX_SIZE:-65536}"

case "$ARM" in
  D|E|F)
    QUANT="UD-Q4_K_XL"
    ;;
  G)
    QUANT="UD-Q6_K_XL"
    ;;
  H)
    QUANT="UD-Q8_K_XL"
    ;;
  *)
    echo "usage: $0 {D|E|F|G|H} [--print]" >&2
    exit 64
    ;;
esac

MODEL="$GGUF_DIR/Qwen3.8-27B-${QUANT}.gguf"
COMMAND=(
  "$LLAMA_BIN"
  -m "$MODEL"
  --host 0.0.0.0
  --port 8080
  --ctx-size "$CTX_SIZE"
  --n-gpu-layers all
  --flash-attn on
  --parallel 1
  --jinja
  --reasoning-preserve
  --chat-template-kwargs '{"preserve_thinking":true,"reasoning_effort":"xhigh"}'
  --metrics
)

case "$ARM" in
  D)
    COMMAND+=(--no-cache-prompt)
    ;;
  E)
    # Canonical llama.cpp prompt-cache defaults, without speculative decoding.
    ;;
  F|G|H)
    COMMAND+=(
      --spec-type draft-mtp
      --spec-draft-model "$MTP_FILE"
      --spec-draft-n-max 3
    )
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

if [[ ! -f "$MODEL" ]]; then
  echo "pinned GGUF is missing: $MODEL" >&2
  exit 66
fi
case "$ARM" in
  F|G|H)
    if [[ ! -f "$MTP_FILE" ]]; then
      echo "pinned MTP sidecar is missing: $MTP_FILE" >&2
      exit 66
    fi
    ;;
esac

exec "${COMMAND[@]}"
