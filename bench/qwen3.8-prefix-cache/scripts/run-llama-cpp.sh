#!/usr/bin/env bash
set -euo pipefail

ARM="${1:-}"
MODE="${2:-}"
LLAMA_BIN="${QWEN38_LLAMA_SERVER_BIN:-llama-server}"
GGUF_REPO="${QWEN38_GGUF_REPO:-unsloth/Qwen3.8-27B-GGUF}"
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

MODEL="${GGUF_REPO}:${QUANT}"
COMMAND=(
  "$LLAMA_BIN"
  -hf "$MODEL"
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
    COMMAND+=(--spec-type draft-mtp --spec-draft-n-max 3)
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
