#!/usr/bin/env bash
# Starts the Splash engine (Inco AI) as an OpenAI-compatible server for one arm.
# Arms: K = mlx-community 8bit target + DFlash2 drafter, defaults from splash-flags.env.
# env: SPLASH_MODEL (target dir, required), SPLASH_DRAFTER (drafter dir, optional), QWEN38_CTX_SIZE (default 32768),
#      QWEN38_SPLASH_EXPECTED_VERSION (checked against `splash --version`), QWEN38_SPLASH_PORT (default 8585)
# usage: run-splash.sh K [--print]
set -euo pipefail
ARM="${1:?usage: $0 K [--print]}"; shift
PRINT=""; [[ "${1:-}" == --print ]] && PRINT=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/splash-flags.env
source "$HERE/config/splash-flags.env"
[[ "$ARM" == K ]] || { echo "run-splash: unknown arm: $ARM" >&2; exit 64; }
MODEL="${SPLASH_MODEL:?SPLASH_MODEL is required}"
CTX="${QWEN38_CTX_SIZE:-32768}"; PORT="${QWEN38_SPLASH_PORT:-8585}"
CMD=("$SPLASH_BIN" "$SPLASH_SERVE_SUBCMD" "$SPLASH_FLAG_MODEL" "$MODEL" "$SPLASH_FLAG_HOST" 0.0.0.0 "$SPLASH_FLAG_PORT" "$PORT")
[[ -n "${SPLASH_FLAG_CTX:-}" ]] && CMD+=("$SPLASH_FLAG_CTX" "$CTX")
[[ -n "${SPLASH_DRAFTER:-}" && -n "${SPLASH_FLAG_DRAFTER:-}" ]] && CMD+=("$SPLASH_FLAG_DRAFTER" "$SPLASH_DRAFTER")
# shellcheck disable=SC2206
[[ -n "${SPLASH_EXTRA_ARGS:-}" ]] && CMD+=($SPLASH_EXTRA_ARGS)
if [[ -n "$PRINT" ]]; then echo "${CMD[*]}"; exit 0; fi
[[ -f "$MODEL/config.json" ]] || { echo "run-splash: missing $MODEL/config.json" >&2; exit 66; }
if [[ -n "${QWEN38_SPLASH_EXPECTED_VERSION:-}" ]]; then
  v="$("$SPLASH_BIN" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
  [[ "$v" == "$QWEN38_SPLASH_EXPECTED_VERSION" ]] || { echo "run-splash: version $v != $QWEN38_SPLASH_EXPECTED_VERSION" >&2; exit 65; }
fi
exec "${CMD[@]}"
