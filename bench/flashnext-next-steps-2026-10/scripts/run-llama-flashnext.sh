#!/usr/bin/env bash
# Launcher of the Flash-Next GGUF arms (test #8): ggml-org IQ4_NL + MTP head Q8_0.
#   GN  llama-server >= b11569, no speculative decoding (decode reference)
#   GM  llama-server >= b11569, --spec-type draft-mtp with the MTP head; --parallel 1 and no --kv-unified
#       (llama.cpp issue #30368: draft-mtp + --kv-unified + --parallel > 1 breaks every request)
#   GX  mlx-serve 26.10.2-pre-release.1 with the same GGUF (embedded llama.cpp). The MTP head is passed with
#       the first flag the binary's --help lists among --mtp-model, --mtp-draft, --drafter; with none, the
#       arm runs with --mtp only and the boot log says so.
# Env: QWEN38_GGUF_DIR (pack dir), QWEN38_CTX_SIZE, QWEN38_LLAMA_SERVER_BIN, QWEN38_MLX_SERVE_BIN.
# usage: run-llama-flashnext.sh <GN|GM|GX> [--print]
set -euo pipefail
ARM="${1:-}"; MODE="${2:-}"
case "$ARM" in GN|GM|GX) ;; *) echo "usage: $0 {GN|GM|GX} [--print]" >&2; exit 64 ;; esac
case "$MODE" in ""|--print) ;; *) echo "unknown option: $MODE" >&2; exit 64 ;; esac
GGUF_DIR="${QWEN38_GGUF_DIR:?QWEN38_GGUF_DIR is required}"
CTX="${QWEN38_CTX_SIZE:-32768}"
# The first shard of a split GGUF loads the rest; a single-file GGUF is its own first shard.
# A missing dir (e.g. --print before the download) must not abort under pipefail: fall back to a MISSING path.
MODEL="$( (find "$GGUF_DIR" -name '*.gguf' -path '*IQ4_NL*' ! -name 'mtp-*' 2>/dev/null || true) | sort | head -1)"
MTP="$( (find "$GGUF_DIR" -name 'mtp-*Q8_0*.gguf' 2>/dev/null || true) | sort | head -1)"
MODEL="${MODEL:-$GGUF_DIR/MISSING-IQ4_NL.gguf}"; MTP="${MTP:-$GGUF_DIR/MISSING-mtp-Q8_0.gguf}"

if [[ "$ARM" == GX ]]; then
  BIN="${QWEN38_MLX_SERVE_BIN:?QWEN38_MLX_SERVE_BIN is required for GX}"
  COMMAND=("$BIN" --model "$MODEL" --serve --host 0.0.0.0 --port 11234 --ctx-size "$CTX" --metrics --mtp
           --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64)
  MTP_FLAG=""
  if [[ -x "$BIN" ]]; then
    HELP="$("$BIN" --help 2>&1 || true)"
    for f in --mtp-model --mtp-draft --drafter; do
      if grep -q -- "$f" <<<"$HELP"; then MTP_FLAG="$f"; break; fi
    done
  fi
  if [[ -n "$MTP_FLAG" ]]; then COMMAND+=("$MTP_FLAG" "$MTP"); else echo "run-llama-flashnext: GX without an MTP head flag" >&2; fi
else
  BIN="${QWEN38_LLAMA_SERVER_BIN:?QWEN38_LLAMA_SERVER_BIN is required}"
  COMMAND=("$BIN" -m "$MODEL" --alias flashnext-gguf --host 0.0.0.0 --port 8080 --ctx-size "$CTX"
           --n-gpu-layers all --flash-attn on --parallel 1 --jinja
           --chat-template-kwargs '{"preserve_thinking":true,"reasoning_effort":"xhigh"}' --metrics)
  [[ "$ARM" == GM ]] && COMMAND+=(--spec-type draft-mtp --spec-draft-model "$MTP" --spec-draft-n-max 3)
fi

if [[ "$MODE" == --print ]]; then printf '%q ' "${COMMAND[@]}"; printf '\n'; exit 0; fi
[[ -f "$MODEL" ]] || { echo "GGUF IQ4_NL missing under $GGUF_DIR" >&2; exit 66; }
[[ "$ARM" == GN || -f "$MTP" ]] || { echo "MTP head mtp-*Q8_0*.gguf missing under $GGUF_DIR" >&2; exit 66; }
exec "${COMMAND[@]}"
