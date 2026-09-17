#!/usr/bin/env bash
# Serve the support model beside the Flash-Next driver, on port 11235.
#
#   s1  MiniCPM5-2B-OptiQ-4bit   (mixed 4/8, 1.8 GB)   first choice
#   s2  MiniCPM5-2B-8bit         (8-bit, 2.5 GB)       quality reference
#   s3  gemma-4-E4B-it-MLX-8bit  (8-bit, 8.97 GB)      incumbent tiny slot
#
# s1/s2 run under `optiq serve` (venv at ~/.local/opt/minicpm5-support/venv),
# which patches mlx-lm to parse MiniCPM5's `<function name=...>` into OpenAI
# tool_calls and exposes `<model>:no-think` / `:think` variants. s3 is a plain
# mlx-lm model; the same server loads it. The driver's environment is never
# touched.
#
# Env overrides: SUPPORT_PORT (default 11235), SUPPORT_HOST (0.0.0.0),
#                SUPPORT_MODEL (absolute path), SUPPORT_MAX_CONCURRENT (1),
#                SUPPORT_KV_BITS (4|8, default off = fp16 KV),
#                SUPPORT_KV_CONFIG (path to a kv_config.json),
#                SUPPORT_NGRAM_DRAFT (int, default off).
# Add --print to show the command without starting.
set -euo pipefail

ARM="${1:-s1}"
PRINT=""
for arg in "${@:2}"; do
  case "$arg" in
    --print) PRINT=1 ;;
    *) echo "usage: $0 [s1|s2|s3] [--print]" >&2; exit 64 ;;
  esac
done

VENV="$HOME/.local/opt/minicpm5-support/venv"
OPTIQ="$VENV/bin/optiq"
# gemma-4-E4B é `Gemma4ForConditionalGeneration` (VLM): mlx_lm.server (0.31.3)
# não carrega e o mlx_vlm 0.6.3 do oMLX também não. O mlx_vlm 0.7.1 (venv
# dedicado) carrega e serve tool_calls corretamente.
VLM_SERVER="$HOME/.local/opt/gemma4-support/venv/bin/mlx_vlm.server"
ROOT="$HOME/.cache/local-llms/minicpm5-2b-support"
HOST="${SUPPORT_HOST:-0.0.0.0}"
PORT="${SUPPORT_PORT:-11235}"
MAXC="${SUPPORT_MAX_CONCURRENT:-1}"
KV_ARGS=()
[[ -n "${SUPPORT_KV_BITS:-}" ]] && KV_ARGS=(--kv-bits "$SUPPORT_KV_BITS")
[[ -n "${SUPPORT_KV_CONFIG:-}" ]] && KV_ARGS=(--kv-config "$SUPPORT_KV_CONFIG")
[[ -n "${SUPPORT_NGRAM_DRAFT:-}" ]] && KV_ARGS+=(--ngram-draft "$SUPPORT_NGRAM_DRAFT")

case "$ARM" in
  s1) MODEL="${SUPPORT_MODEL:-$ROOT/mlx-community-MiniCPM5-2B-OptiQ-4bit-d1392929adb5693640daeebe6b45e12a07a60b5a}"
      COMMAND=("$OPTIQ" serve --model "$MODEL" --host "$HOST" --port "$PORT" --max-concurrent "$MAXC" ${KV_ARGS[@]+"${KV_ARGS[@]}"}) ;;
  s2) MODEL="${SUPPORT_MODEL:-$ROOT/mlx-community-MiniCPM5-2B-8bit-2d20e8e672ce892d50f7265bfd3fc9b59b718f2a}"
      COMMAND=("$OPTIQ" serve --model "$MODEL" --host "$HOST" --port "$PORT" --max-concurrent "$MAXC" ${KV_ARGS[@]+"${KV_ARGS[@]}"}) ;;
  s3) MODEL="${SUPPORT_MODEL:-$HOME/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-MLX-8bit}"
      COMMAND=("$VLM_SERVER" --model "$MODEL" --host "$HOST" --port "$PORT") ;;
  *) echo "arm desconhecido: $ARM" >&2; exit 64 ;;
esac

if [[ -n "$PRINT" ]]; then
  printf '%q ' "${COMMAND[@]}"; printf '\n'
  exit 0
fi

[[ -x "${COMMAND[0]}" ]] || { echo "runtime not found: ${COMMAND[0]}" >&2; exit 66; }
[[ -f "$MODEL/config.json" ]] || { echo "model not found: $MODEL" >&2; exit 66; }
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $PORT is already in use; stop the running support server first" >&2
  exit 69
fi
echo "support ($ARM) on http://$HOST:$PORT/v1  model=$MODEL" >&2
exec "${COMMAND[@]}"