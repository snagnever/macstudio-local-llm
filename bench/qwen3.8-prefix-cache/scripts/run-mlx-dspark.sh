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

EXPECTED_VERSION="${QWEN38_MLX_DSPARK_EXPECTED_VERSION:-0.15.0}"
DOCTOR_JSON="$($MLX_DSPARK_BIN doctor --json 2>/dev/null)" || true
ACTUAL_VERSION="$(DOCTOR_JSON="$DOCTOR_JSON" python3 -c 'import json, os; report=json.loads(os.environ["DOCTOR_JSON"]); print((report.get("environment") or {}).get("version") or "")' 2>/dev/null)" || {
  echo "failed to determine mlx-dspark version from doctor --json" >&2
  exit 69
}
[[ "$ACTUAL_VERSION" == "$EXPECTED_VERSION" ]] || { echo "mlx-dspark version mismatch: expected $EXPECTED_VERSION, got ${ACTUAL_VERSION:-unknown}" >&2; exit 65; }

CONFIG_ARGS=(python3 "$CONFIG_TOOL" --config "$CONFIG" --target-path "$MLX_DSPARK_TARGET_PATH")
[[ -n "${MLX_DSPARK_DSPARK_PATH:-}" ]] && CONFIG_ARGS+=(--dspark-path "$MLX_DSPARK_DSPARK_PATH")
[[ -n "${MLX_DSPARK_DFLASH2_PATH:-}" ]] && CONFIG_ARGS+=(--dflash-path "$MLX_DSPARK_DFLASH2_PATH")
CONTEXT_WINDOW="${QWEN38_CTX_SIZE:-65536}"
CONFIG_ARGS+=(--context-window "$CONTEXT_WINDOW")

if [[ "$ARM" != "auto-smoke" ]]; then
  command_shell="$("${CONFIG_ARGS[@]}" --arm "$ARM" --command-shell)"
  # The config tool shell-quotes every argument; this only reconstructs that fixed argv.
  eval "set -- $command_shell"
  COMMAND=("$MLX_DSPARK_BIN" "${@:2}")
  if [[ "$OPTION" == "--print" ]]; then printf '%q ' "${COMMAND[@]}"; printf '\n'; exit 0; fi
  exec "${COMMAND[@]}"
fi

# Pin DFlash mode when a local drafter path is supplied. In v0.15.0, auto + an
# explicit drafter intentionally resolves to DSpark, regardless of its config.
"${CONFIG_ARGS[@]}" --arm S --print-command >/dev/null
AUTO_COMMAND=("$MLX_DSPARK_BIN" serve --model "$MLX_DSPARK_TARGET_PATH" --mode dflash --drafter "$MLX_DSPARK_DFLASH2_PATH" --host 0.0.0.0 --port 8484 --context-window "$CONTEXT_WINDOW" --reasoning-effort xhigh --max-batch 1)
if [[ "$OPTION" == "--print" ]]; then printf '%q ' "${AUTO_COMMAND[@]}"; printf '\n'; exit 0; fi
if python3 -c 'import socket, sys; s=socket.socket(); s.settimeout(0.2); status=s.connect_ex(("127.0.0.1", 8484)); s.close(); sys.exit(0 if status == 0 else 1)'; then
  echo "auto-smoke refused: port 8484 is already in use" >&2
  exit 69
fi
mkdir -p "$CAMPAIGN/logs"
"${AUTO_COMMAND[@]}" >"$CAMPAIGN/logs/mlx-dspark-auto-smoke.log" 2>&1 &
PID=$!
cleanup() { kill "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for _ in $(seq 1 "${QWEN38_HEALTH_ATTEMPTS:-120}"); do
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID" 2>/dev/null || child_status=$?
    echo "auto-smoke child exited before health (status ${child_status:-0})" >&2
    exit 1
  fi
  if HEALTH="$(curl --silent --fail http://127.0.0.1:8484/health 2>/dev/null)"; then
    kill -0 "$PID" 2>/dev/null || { echo "auto-smoke child exited before health validation" >&2; exit 1; }
    HEALTH="$HEALTH" EXPECTED_TARGET="$MLX_DSPARK_TARGET_PATH" EXPECTED_DRAFTER="$MLX_DSPARK_DFLASH2_PATH" \
      python3 -c 'import json, os, sys; h=json.loads(os.environ["HEALTH"]); ok=h.get("status") == "ok" and h.get("mode") == "dflash" and h.get("target") == os.environ["EXPECTED_TARGET"] and h.get("drafter") == os.environ["EXPECTED_DRAFTER"]; sys.exit(0 if ok else 1)' && exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    wait "$PID" 2>/dev/null || child_status=$?
    echo "auto-smoke child exited before health (status ${child_status:-0})" >&2
    exit 1
  fi
  sleep 1
done
echo "auto-smoke failed: /health did not resolve dflash with the expected DFlash2 drafter" >&2
exit 1
