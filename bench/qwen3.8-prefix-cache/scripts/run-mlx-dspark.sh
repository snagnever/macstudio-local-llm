#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CAMPAIGN="$ROOT/bench/qwen3.8-prefix-cache"
CONFIG="$CAMPAIGN/config/mlx-dspark-arms.json"
CONFIG_TOOL="$CAMPAIGN/scripts/mlx_dspark_config.py"
ARM="${1:-}"
OPTION="${2:-}"
MLX_DSPARK_BIN="${MLX_DSPARK_BIN:-mlx-dspark}"

case "$ARM" in P|Q|R|S|auto-smoke) ;; *) echo "usage: $0 {P|Q|R|S|auto-smoke} [--print]" >&2; exit 64;; esac
case "$OPTION" in ""|--print) ;; *) echo "unknown option: $OPTION" >&2; exit 64;; esac
[[ -n "${MLX_DSPARK_TARGET_PATH:-}" ]] || { echo "MLX_DSPARK_TARGET_PATH is required" >&2; exit 64; }
if [[ "$ARM" == "R" ]]; then [[ -n "${MLX_DSPARK_DSPARK_PATH:-}" ]] || { echo "MLX_DSPARK_DSPARK_PATH is required for R" >&2; exit 64; }; fi
if [[ "$ARM" == "S" || "$ARM" == "auto-smoke" ]]; then [[ -n "${MLX_DSPARK_DFLASH2_PATH:-}" ]] || { echo "MLX_DSPARK_DFLASH2_PATH is required" >&2; exit 64; }; fi

EXPECTED_VERSION="v0.15.0"
ACTUAL_VERSION="$($MLX_DSPARK_BIN --version)" || { echo "failed to determine mlx-dspark version" >&2; exit 69; }
[[ "$ACTUAL_VERSION" == *"0.15.0"* ]] || { echo "mlx-dspark version mismatch: expected $EXPECTED_VERSION, got $ACTUAL_VERSION" >&2; exit 65; }

CONFIG_ARGS=(python3 "$CONFIG_TOOL" --config "$CONFIG" --target-path "$MLX_DSPARK_TARGET_PATH")
[[ -n "${MLX_DSPARK_DSPARK_PATH:-}" ]] && CONFIG_ARGS+=(--dspark-path "$MLX_DSPARK_DSPARK_PATH")
[[ -n "${MLX_DSPARK_DFLASH2_PATH:-}" ]] && CONFIG_ARGS+=(--dflash-path "$MLX_DSPARK_DFLASH2_PATH")

if [[ "$ARM" != "auto-smoke" ]]; then
  command_shell="$("${CONFIG_ARGS[@]}" --arm "$ARM" --command-shell)"
  # The config tool shell-quotes every argument; this only reconstructs that fixed argv.
  eval "set -- $command_shell"
  COMMAND=("$MLX_DSPARK_BIN" "${@:2}")
  if [[ "$OPTION" == "--print" ]]; then printf '%q ' "${COMMAND[@]}"; printf '\n'; exit 0; fi
  exec "${COMMAND[@]}"
fi

# The auto probe intentionally leaves the drafter unspecified: v0.15.0 must resolve it.
"${CONFIG_ARGS[@]}" --arm S --print-command >/dev/null
mkdir -p "$CAMPAIGN/logs"
AUTO_COMMAND=("$MLX_DSPARK_BIN" serve --model "$MLX_DSPARK_TARGET_PATH" --mode auto --host 0.0.0.0 --port 8484 --context-window 65536 --reasoning-effort xhigh --max-batch 1)
if [[ "$OPTION" == "--print" ]]; then printf '%q ' "${AUTO_COMMAND[@]}"; printf '\n'; exit 0; fi
"${AUTO_COMMAND[@]}" >"$CAMPAIGN/logs/mlx-dspark-auto-smoke.log" 2>&1 &
PID=$!
cleanup() { kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for _ in $(seq 1 "${QWEN38_HEALTH_ATTEMPTS:-120}"); do
  if HEALTH="$(curl --silent --fail http://127.0.0.1:8484/health 2>/dev/null)"; then
    HEALTH="$HEALTH" EXPECTED_DRAFTER="incoai/Qwen3.8-27B-DFlash2" EXPECTED_PATH="$MLX_DSPARK_DFLASH2_PATH" \
      python3 -c 'import json, os, sys; h=json.loads(os.environ["HEALTH"]); expected=os.environ["EXPECTED_DRAFTER"]; actual=h.get("drafter"); ok=h.get("status") == "ok" and h.get("mode") == "dflash" and actual in {expected, os.environ["EXPECTED_PATH"]}; sys.exit(0 if ok else 1)' && exit 0
  fi
  sleep 1
done
echo "auto-smoke failed: /health did not resolve dflash with the expected DFlash2 drafter" >&2
exit 1
