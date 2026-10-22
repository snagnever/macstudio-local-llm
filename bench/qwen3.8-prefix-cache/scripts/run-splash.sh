#!/usr/bin/env bash
# Starts the Splash engine (Inco AI) as an OpenAI-compatible server for one arm.
# Arms: K = mlx-community 8bit target (a Hub ID, Splash refuses local target dirs) + DFlash2 draft pinned to a
# local directory, defaults from splash-flags.env. KF = Flash-Next GGUF (Hub ID OWNER/REPO:VARIANT, Splash 1.4.0+)
# with the draft Splash selects itself (stack-updates-2026-10).
# env: SPLASH_MODEL (Hub ID OWNER/REPO[:VARIANT], required), SPLASH_REVISION (optional), SPLASH_DRAFTER (local
#      DFlash2 draft dir, optional), QWEN38_CTX_SIZE (default 32768),
#      QWEN38_SPLASH_EXPECTED_VERSION (checked against `splash --version`), QWEN38_SPLASH_PORT (default 8585),
#      QWEN38_SPLASH_BIN (default SPLASH_BIN of splash-flags.env), QWEN38_SPLASH_EXTRA_ARGS (appended after
#      SPLASH_EXTRA_ARGS, which splash-flags.env sets)
# usage: run-splash.sh K|KF [--print]
set -euo pipefail
ARM="${1:?usage: $0 K|KF [--print]}"; shift
PRINT=""; [[ "${1:-}" == --print ]] && PRINT=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/splash-flags.env
source "$HERE/config/splash-flags.env"
SPLASH_BIN="${QWEN38_SPLASH_BIN:-$SPLASH_BIN}"
[[ "$ARM" == K || "$ARM" == KF ]] || { echo "run-splash: unknown arm: $ARM" >&2; exit 64; }
MODEL="${SPLASH_MODEL:?SPLASH_MODEL is required}"
CTX="${QWEN38_CTX_SIZE:-32768}"; PORT="${QWEN38_SPLASH_PORT:-8585}"
CMD=("$SPLASH_BIN" "$SPLASH_SERVE_SUBCMD" "$SPLASH_FLAG_MODEL" "$MODEL" "$SPLASH_FLAG_HOST" 0.0.0.0 "$SPLASH_FLAG_PORT" "$PORT")
[[ -n "${SPLASH_FLAG_CTX:-}" ]] && CMD+=("$SPLASH_FLAG_CTX" "$CTX")
[[ -n "${SPLASH_REVISION:-}" && -n "${SPLASH_FLAG_REVISION:-}" ]] && CMD+=("$SPLASH_FLAG_REVISION" "$SPLASH_REVISION")
[[ -n "${SPLASH_DRAFTER:-}" && -n "${SPLASH_FLAG_DRAFTER:-}" ]] && CMD+=("$SPLASH_FLAG_DRAFTER" "$SPLASH_DRAFTER")
# shellcheck disable=SC2206
[[ -n "${SPLASH_EXTRA_ARGS:-}" ]] && CMD+=($SPLASH_EXTRA_ARGS)
# shellcheck disable=SC2206
[[ -n "${QWEN38_SPLASH_EXTRA_ARGS:-}" ]] && CMD+=($QWEN38_SPLASH_EXTRA_ARGS)
if [[ -n "$PRINT" ]]; then echo "${CMD[*]}"; exit 0; fi
if [[ -d "$MODEL" ]]; then
  [[ -f "$MODEL/config.json" ]] || { echo "run-splash: missing $MODEL/config.json" >&2; exit 66; }
fi
if [[ -n "${SPLASH_DRAFTER:-}" ]]; then
  [[ -d "$SPLASH_DRAFTER" ]] || { echo "run-splash: draft model dir not found: $SPLASH_DRAFTER" >&2; exit 66; }
fi
if [[ -n "${QWEN38_SPLASH_EXPECTED_VERSION:-}" ]]; then
  v="$("$SPLASH_BIN" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
  [[ "$v" == "$QWEN38_SPLASH_EXPECTED_VERSION" ]] || { echo "run-splash: version $v != $QWEN38_SPLASH_EXPECTED_VERSION" >&2; exit 65; }
fi
exec "${CMD[@]}"
