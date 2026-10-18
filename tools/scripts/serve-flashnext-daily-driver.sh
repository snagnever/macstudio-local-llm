#!/usr/bin/env bash
# Start the Qwen3.8-Flash-Next daily driver: Swift 1.5 (Dankpaws MLX-4.7bpw) on mlx-serve 26.10.1.
# Promoted by bench/swift15-flashnext-2026-10 (2026-10-11): same quality as the iQ-MLX-4.7bpw pack, 2-3x less
# thinking time. Rollback: FLASHNEXT_MODEL=<cache>/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c...
# Profiles (the configs measured in bench/qwen38-flashnext-daily-driver-2026-09):
#   daily  (default) 131072 tokens, MTP, prefix cache 16GB RAM / 100GB disk / 64 entries
#                    measured with this pack in bench/swift15-flashnext-2026-10 (T_turno 7.9 s at 32K, 8.6 s at 128K)
#   512k             524288 tokens via YaRN 2.0 + 4-bit KV; memory at the edge, close heavy apps first
#                    measured with Swift 1.5 in bench/flashnext-next-steps-2026-10 (Task 2, 3 reps): T_turno 13.3 s,
#                    min free 0.01 GB, needles 13/13; 8-bit KV refused some prefills at 512K (PrefillDoesNotFit)
#   256k             262144 tokens for two long sessions at once: prefix cache cut to 4GB RAM (SSD restores cost
#                    ~1 s per warm turn); measured in bench/flashnext-concurrency-2026-10 (Etapa 1b, w1c2m4).
#                    With the daily 16GB cache a second 256K prompt gets PrefillDoesNotFit.
# Concurrency: mlx-serve 26.10.1 batches decode at its default --max-concurrent 1, so two Claude Code sessions
#   already share the driver; each runs at about half the solo decode speed (bench/flashnext-concurrency-2026-10).
# Overrides: FLASHNEXT_PORT (default 11234), FLASHNEXT_HOST (default 0.0.0.0), FLASHNEXT_BIN, FLASHNEXT_MODEL,
#            FLASHNEXT_MAX_CONCURRENT (opt-in --max-concurrent; no measured effect on 26.10.1; 512k forces 1).
#            Add --print to show the command without starting.
set -euo pipefail

PROFILE="daily"
PRINT=""
for arg in "$@"; do
  case "$arg" in
    daily|256k|512k) PROFILE="$arg" ;;
    --print) PRINT=1 ;;
    *) echo "usage: $0 [daily|256k|512k] [--print]" >&2; exit 64 ;;
  esac
done

BIN="${FLASHNEXT_BIN:-$HOME/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve}"
MODEL="${FLASHNEXT_MODEL:-$HOME/.cache/local-llms/qwen3.8-prefix-cache/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0}"
HOST="${FLASHNEXT_HOST:-0.0.0.0}"
PORT="${FLASHNEXT_PORT:-11234}"
MAX_CONCURRENT="${FLASHNEXT_MAX_CONCURRENT:-}"
PREFIX_CACHE_MEM=16GB
case "$PROFILE" in
  256k) PREFIX_CACHE_MEM=4GB; MAX_CONCURRENT=2 ;;
  512k) MAX_CONCURRENT=1 ;;
esac

COMMAND=(
  "$BIN"
  --model "$MODEL"
  --serve --host "$HOST" --port "$PORT"
  --metrics
  --mtp
  --ssm-checkpoint-max 16
  --prefix-cache-mem "$PREFIX_CACHE_MEM" --prefix-cache-disk 100GB --prefix-cache-entries 64
)

case "$PROFILE" in
  daily)
    COMMAND+=(--ctx-size 131072)
    ;;
  256k)
    COMMAND+=(--ctx-size 262144)
    ;;
  512k)
    COMMAND+=(
      --ctx-size 524288
      --kv-quant 4
      --config-overrides '{"text_config":{"rope_parameters":{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":262144},"max_position_embeddings":524288}}'
    )
    ;;
esac
[[ -n "$MAX_CONCURRENT" ]] && COMMAND+=(--max-concurrent "$MAX_CONCURRENT")

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
  echo "512k profile: memory runs at the edge (min free ~0.01-0.05 GB measured). Close heavy apps." >&2
fi
echo "Flash-Next daily driver ($PROFILE) on http://$HOST:$PORT/v1" >&2
exec "${COMMAND[@]}"
