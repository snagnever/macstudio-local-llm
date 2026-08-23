#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ARM="${1:-}"
OPTION="${2:-}"
MTPLX_BIN="${QWEN38_MTPLX_BIN:-mtplx}"
EXPECTED_VERSION="2.9.1"
MODEL_REVISION="123db8bcc7101455b00d9aad36c0e760c6e7de02"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
MODEL_PATH="$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-$MODEL_REVISION"
CONTEXT_WINDOW="${QWEN38_CTX_SIZE:-32768}"
RUN_ID="${QWEN38_MTPLX_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$ARM-$RANDOM}"

case "$ARM" in V) ;; *) echo "usage: $0 V [--print]" >&2; exit 64;; esac
case "$OPTION" in ""|--print) ;; *) echo "unknown option: $OPTION" >&2; exit 64;; esac
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ || "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
  echo "QWEN38_MTPLX_RUN_ID must be a safe single path component" >&2
  exit 64
fi
[[ -d "$MODEL_PATH" ]] || { echo "missing pinned MTPLX model: $MODEL_PATH" >&2; exit 66; }

STATE_DIR="$ROOT/bench/qwen3.8-prefix-cache/logs/mtplx/$RUN_ID"
CONFIG_PATH="$STATE_DIR/config.toml"
FLIGHT_PATH="$STATE_DIR/flight.jsonl"
COMMAND=(
  env
  "MTPLX_CONFIG=$CONFIG_PATH"
  "MTPLX_FLIGHT_RECORDER=$FLIGHT_PATH"
  "$MTPLX_BIN" serve
  --model "$MODEL_PATH"
  --profile turbo
  --host 127.0.0.1
  --port 8000
  --no-auth
  --depth 3
  --generation-mode mtp
  --context-window "$CONTEXT_WINDOW"
  --ssd-session-cache off
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
if ! grep -Eq '(^|[^0-9])2\.9\.1([^0-9]|$)' <<<"$VERSION_OUTPUT"; then
  echo "MTPLX version mismatch: expected $EXPECTED_VERSION, got ${VERSION_OUTPUT:-unknown}" >&2
  exit 65
fi

mkdir -p "$STATE_DIR"
exec "${COMMAND[@]}"
