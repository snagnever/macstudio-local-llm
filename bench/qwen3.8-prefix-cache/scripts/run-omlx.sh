#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS="$ROOT/bench/qwen3.8-prefix-cache/scripts"
CONFIG="$ROOT/bench/qwen3.8-prefix-cache/config/omlx-arms.json"
ARM="${1:-}"
MODE="${2:-}"
OMLX_BIN="${QWEN38_OMLX_BIN:-omlx}"
EXPECTED_OMLX_VERSION="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["omlx_version"])' "$CONFIG")"

case "$ARM" in
  I|J|K|L|M|N|O|T|U|W|X) ;;
  *)
    echo "usage: $0 {I|J|K|L|M|N|O|T|U|W|X} [--print]" >&2
    exit 64
    ;;
esac

if [[ -n "$MODE" && "$MODE" != "--print" ]]; then
  echo "unknown option: $MODE" >&2
  exit 64
fi

if [[ -z "${OMLX_MODEL_ROOT:-}" ]]; then
  echo "OMLX_MODEL_ROOT is required" >&2
  exit 64
fi

case "$ARM" in
  M)
    if [[ -z "${OMLX_DRAFT_2B_PATH:-}" ]]; then
      echo "OMLX_DRAFT_2B_PATH is required for arm M" >&2
      exit 64
    fi
    ;;
  N)
    if [[ -z "${OMLX_DRAFT_08B_PATH:-}" ]]; then
      echo "OMLX_DRAFT_08B_PATH is required for arm N" >&2
      exit 64
    fi
    ;;
  O)
    if [[ -z "${OMLX_ANE_PROFILE:-}" ]]; then
      echo "OMLX_ANE_PROFILE is required for arm O" >&2
      exit 64
    fi
    ;;
esac

RUN_ID="${QWEN38_OMLX_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$ARM-$RANDOM}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ || "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
  echo "QWEN38_OMLX_RUN_ID must be a safe single path component" >&2
  exit 64
fi
OMLX_BASE_PATH="$ROOT/bench/qwen3.8-prefix-cache/logs/omlx/$RUN_ID"
OMLX_MODEL_DIR="$OMLX_MODEL_ROOT"
OMLX_PORT=8000
DFLASH2_REVISION="dedf8df68adfb1afeaf7b7480c0a0243108177b4"
DFLASH2_PATH="${OMLX_DFLASH2_PATH:-$OMLX_MODEL_ROOT/incoai-Qwen3.8-27B-DFlash2-$DFLASH2_REVISION}"

CONFIG_COMMAND=(
  python3 "$SCRIPTS/omlx_config.py"
  --config "$CONFIG"
  --arm "$ARM"
  --base-path "$OMLX_BASE_PATH"
  --model-root "$OMLX_MODEL_ROOT"
)
case "$ARM" in
  M) CONFIG_COMMAND+=(--draft-2b-path "$OMLX_DRAFT_2B_PATH") ;;
  N) CONFIG_COMMAND+=(--draft-08b-path "$OMLX_DRAFT_08B_PATH") ;;
  O) CONFIG_COMMAND+=(--ane-profile "$OMLX_ANE_PROFILE") ;;
  X) CONFIG_COMMAND+=(--dflash2-path "$DFLASH2_PATH") ;;
esac

PROFILE="$("${CONFIG_COMMAND[@]}" --print-profile)"
OMLX_CACHE_ENABLED="$(python3 -c 'import json, sys; print(str(json.loads(sys.stdin.read())["cache_enabled"]).lower())' <<<"$PROFILE")"
export OMLX_BASE_PATH OMLX_MODEL_DIR OMLX_PORT OMLX_CACHE_ENABLED

COMMAND=(env "OMLX_BASE_PATH=$OMLX_BASE_PATH" "OMLX_MODEL_DIR=$OMLX_MODEL_DIR" "OMLX_PORT=$OMLX_PORT" "OMLX_CACHE_ENABLED=$OMLX_CACHE_ENABLED" "$OMLX_BIN" serve)

if [[ "$MODE" == "--print" ]]; then
  printf 'profile=%s\n' "$PROFILE"
  printf '%q ' "${COMMAND[@]}"
  printf '\n'
  exit 0
fi

if [[ "${EXPECTED_OMLX_VERSION#v}" != "0.6.3rc2" ]]; then
  echo "campaign configuration must pin oMLX v0.6.3rc2" >&2
  exit 65
fi
if ! ACTUAL_OMLX_VERSION="$("$OMLX_BIN" --version)"; then
  echo "failed to determine oMLX runtime version" >&2
  exit 69
fi
if [[ "${ACTUAL_OMLX_VERSION#v}" != "${EXPECTED_OMLX_VERSION#v}" ]]; then
  echo "oMLX version mismatch: expected $EXPECTED_OMLX_VERSION, got $ACTUAL_OMLX_VERSION" >&2
  exit 65
fi

exec "${COMMAND[@]}"
