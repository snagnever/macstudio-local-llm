#!/usr/bin/env bash
# Start the Qwen3.8-Flash-Next daily driver: ddalcu mixed-4/8 on mlx-serve 26.9.2.
# Profiles (the exact configs measured in bench/qwen38-flashnext-daily-driver-2026-09):
#   daily  (default) 131072 tokens, MTP, prefix cache 16GB RAM / 100GB disk / 64 entries
#   512k             524288 tokens via YaRN 2.0 + 8-bit KV; memory at the edge, close heavy apps first
# Overrides: FLASHNEXT_PORT (default 11234), FLASHNEXT_HOST (default 0.0.0.0),
#            FLASHNEXT_BIN, FLASHNEXT_MODEL. Add --print to show the command without starting.
set -euo pipefail

PROFILE="daily"
PRINT=""
for arg in "$@"; do
  case "$arg" in
    daily|512k) PROFILE="$arg" ;;
    --print) PRINT=1 ;;
    *) echo "usage: $0 [daily|512k] [--print]" >&2; exit 64 ;;
  esac
done

BIN="${FLASHNEXT_BIN:-$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve}"
MODEL="${FLASHNEXT_MODEL:-$HOME/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd}"
HOST="${FLASHNEXT_HOST:-0.0.0.0}"
PORT="${FLASHNEXT_PORT:-11234}"

COMMAND=(
  "$BIN"
  --model "$MODEL"
  --serve --host "$HOST" --port "$PORT"
  --metrics
  --mtp
  --ssm-checkpoint-max 16
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 64
)

case "$PROFILE" in
  daily)
    COMMAND+=(--ctx-size 131072)
    ;;
  512k)
    COMMAND+=(
      --ctx-size 524288
      --kv-quant 8 --kv-attn-mode fused
      --config-overrides '{"text_config":{"rope_parameters":{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":262144},"max_position_embeddings":524288}}'
    )
    ;;
esac

if [[ -n "$PRINT" ]]; then
  printf '%q ' "${COMMAND[@]}"; printf '\n'
  exit 0
fi

[[ -x "$BIN" ]] || { echo "mlx-serve binary not found: $BIN" >&2; exit 66; }
[[ -f "$MODEL/config.json" ]] || { echo "model not found: $MODEL" >&2; exit 66; }
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $PORT is already in use; stop the running server first" >&2
  exit 69
fi
if [[ "$PROFILE" == "512k" ]]; then
  echo "512k profile: memory runs at the edge (min free ~0.01 GB measured). Close heavy apps." >&2
fi
echo "Flash-Next daily driver ($PROFILE) on http://$HOST:$PORT/v1" >&2
exec "${COMMAND[@]}"
