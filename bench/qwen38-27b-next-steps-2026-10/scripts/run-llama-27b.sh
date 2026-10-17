#!/usr/bin/env bash
# llama-server for the dense Qwen3.8-27B GGUF (ggml-org Q8_0) on port 8080.
# Arms: L27M = --spec-type draft-mtp with the Q8_0 MTP head, n-max 2; L27N = no speculation.
# env: QWEN38_GGUF_DIR (required), QWEN38_CTX_SIZE (default 65536), QWEN38_LLAMA_SERVER_BIN,
#      FLASHNEXT_EFFORT (xhigh|medium|low, default medium; passed via --chat-template-kwargs)
# usage: run-llama-27b.sh L27M|L27N [--print]
set -euo pipefail
ARM="${1:?usage: $0 L27M|L27N [--print]}"; shift
PRINT=""; [[ "${1:-}" == --print ]] && PRINT=1
BIN="${QWEN38_LLAMA_SERVER_BIN:-$HOME/.local/opt/qwen38/llama-b11569/llama-server}"
DIR="${QWEN38_GGUF_DIR:?QWEN38_GGUF_DIR is required}"
CTX="${QWEN38_CTX_SIZE:-65536}"; EFFORT="${FLASHNEXT_EFFORT:-medium}"
case "$EFFORT" in xhigh|medium|low) ;; *) echo "run-llama-27b: bad effort $EFFORT" >&2; exit 64 ;; esac
MAIN="$(ls "$DIR"/Qwen3.8-27B-Q8_0*.gguf 2>/dev/null | grep -v '^.*/mtp-' | head -1 || true)"
MTP="$(ls "$DIR"/mtp-Qwen3.8-27B-Q8_0.gguf 2>/dev/null | head -1 || true)"
[[ -n "$PRINT" || -f "$MAIN" ]] || { echo "run-llama-27b: no Q8_0 gguf in $DIR" >&2; exit 66; }
MAIN="${MAIN:-$DIR/Qwen3.8-27B-Q8_0.gguf}"; MTP="${MTP:-$DIR/mtp-Qwen3.8-27B-Q8_0.gguf}"
CMD=("$BIN" -m "$MAIN" --host 0.0.0.0 --port 8080 --alias qwen38-27b-gguf -c "$CTX" -np 1 --no-kv-unified -fa on -ngl 99
     --jinja --chat-template-kwargs "{\"reasoning_effort\":\"$EFFORT\",\"preserve_thinking\":true}" --metrics)
case "$ARM" in
  L27M) CMD+=(--spec-type draft-mtp -md "$MTP" --spec-draft-n-max 2) ;;
  L27N) ;;
  *) echo "run-llama-27b: unknown arm: $ARM" >&2; exit 64 ;;
esac
if [[ -n "$PRINT" ]]; then echo "${CMD[*]}"; exit 0; fi
[[ "$ARM" == L27N || -f "$MTP" ]] || { echo "run-llama-27b: missing $MTP" >&2; exit 66; }
exec "${CMD[@]}"
