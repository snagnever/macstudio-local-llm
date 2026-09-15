#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ARM="${1:-}"
OPTION="${2:-}"
MTPLX_BIN="${QWEN38_MTPLX_BIN:-mtplx}"
EXPECTED_VERSION="${QWEN38_MTPLX_EXPECTED_VERSION:-2.9.2}"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
CONTEXT_WINDOW="${QWEN38_CTX_SIZE:-32768}"
RUN_ID="${QWEN38_MTPLX_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$ARM-$RANDOM}"

# V = Optimized Speed (4-bit body); Y = Optimized Quality (8-bit). Same runtime
# config so V vs Y isolates the checkpoint recipe.
case "$ARM" in
  V) MODEL_REVISION="123db8bcc7101455b00d9aad36c0e760c6e7de02"
     MODEL_NAME="Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed" ;;
  Y) MODEL_REVISION="09f71b39a75c416be3c974840b53f9fbe9aa1841"
     MODEL_NAME="Youssofal-Qwen3.8-27B-MTPLX-Optimized-Quality" ;;
  Z) MODEL_REVISION="4b3533770e01217f9b523f337b4597fd4ca50eea"
     MODEL_NAME="Youssofal-Qwen3.8-27B-MTPLX-Optimized-Quality-FP16" ;;
  FX) MODEL_REVISION="6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"
      MODEL_NAME="Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed" ;;
  *) echo "usage: $0 {V|Y|Z|FX} [--print]" >&2; exit 64;;
esac
MODEL_PATH="$MODEL_ROOT/$MODEL_NAME-$MODEL_REVISION"
case "$OPTION" in ""|--print) ;; *) echo "unknown option: $OPTION" >&2; exit 64;; esac
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ || "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
  echo "QWEN38_MTPLX_RUN_ID must be a safe single path component" >&2
  exit 64
fi
[[ -d "$MODEL_PATH" ]] || { echo "missing pinned MTPLX model: $MODEL_PATH" >&2; exit 66; }

STATE_DIR="$ROOT/bench/qwen3.8-prefix-cache/logs/mtplx/$RUN_ID"
CONFIG_PATH="$STATE_DIR/config.toml"
FLIGHT_PATH="$STATE_DIR/flight.jsonl"
# FX (Flash-Next, pack MTPLX): o vendor roda SSD session cache ON e e o caminho seguro de memoria
# na linha 2.10+. Os arms da densa (V/Y/Z) mantem OFF para nao mudar a comparacao historica.
MTPLX_SSD_DEFAULT=off
[[ "$ARM" == "FX" ]] && MTPLX_SSD_DEFAULT=on
COMMAND=(
  env
  "MTPLX_CONFIG=$CONFIG_PATH"
  "MTPLX_FLIGHT_RECORDER=$FLIGHT_PATH"
  "$MTPLX_BIN" serve
  --model "$MODEL_PATH"
  --profile "${QWEN38_MTPLX_PROFILE:-turbo}"
  --host 127.0.0.1
  --port 8000
  --no-auth
  --depth "${QWEN38_MTPLX_DEPTH:-3}"
  --generation-mode "${QWEN38_MTPLX_GENERATION_MODE:-mtp}"
  --context-window "$CONTEXT_WINDOW"
  --ssd-session-cache "${QWEN38_MTPLX_SSD_SESSION_CACHE:-$MTPLX_SSD_DEFAULT}"
  --ssd-session-cache-dir "$STATE_DIR/ssd-session-cache"
  --reasoning on
  --reasoning-effort xhigh
  --preserve-thinking on
  --default-temperature 1.0
  --default-top-p 0.95
  --default-top-k 20
)

if [[ "$OPTION" == "--print" ]]; then
  printf '%q ' "${COMMAND[@]}"
  printf '\n'
  exit 0
fi

VERSION_OUTPUT="$($MTPLX_BIN --version)" || {
  echo "failed to determine MTPLX runtime version" >&2
  exit 69
}
if ! grep -Eq "(^|[^0-9])${EXPECTED_VERSION//./\\.}([^0-9]|\$)" <<<"$VERSION_OUTPUT"; then
  echo "MTPLX version mismatch: expected $EXPECTED_VERSION, got ${VERSION_OUTPUT:-unknown}" >&2
  exit 65
fi

mkdir -p "$STATE_DIR"
exec "${COMMAND[@]}"
