#!/usr/bin/env bash
# P1 — A/B de runtime do mlx-serve no Flash-Next: 26.9.1 (baseline) vs 26.9.2.
# Isola uma variavel: so o binario muda. Mesmo modelo, mesma config FS (--mtp,
# prefix-cache 16GB/100GB/64), mesmo protocolo do cache_probe.
#
# Uso: run-p1-mlxserve-ab.sh <v26.9.1|v26.9.2|both> [ctx]
#   ctx default 32768. Reprobar o baseline na mesma sessao antes de declarar ganho.
set -euo pipefail

VER="${1:-}"
CTX="${2:-32768}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
RESULTS="$REPO/bench/qwen38-updates-2026-09/results"
LOGS="$REPO/bench/qwen38-updates-2026-09/logs"

MODEL_DIR="$HOME/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
MODEL_REV="ef5b919d31534faa1997666f1a22d362cd6383cd"
PORT=11234
BASE="http://127.0.0.1:${PORT}"

case "$VER" in
  v26.9.1|v26.9.2|both) ;;
  *) echo "uso: $0 <v26.9.1|v26.9.2|both> [ctx]" >&2; exit 64 ;;
esac

SERVER_PID=""
cleanup() { [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT

wait_port_free() {
  for _ in $(seq 1 30); do
    lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || return 0
    sleep 1
  done
  echo "porta ${PORT} nao liberou" >&2; return 1
}

server_ready() {
  curl -s --max-time 3 "$BASE/v1/models" 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    sys.exit(0 if d["data"][0].get("state") == "ready" else 1)
except Exception:
    sys.exit(1)
'
}

run_one() {
  local ver="$1"
  local bin="$HOME/.local/opt/qwen38/mlx-serve-${ver}/mlx-serve"
  [[ -x "$bin" ]] || { echo "binario ausente: $bin" >&2; exit 66; }
  [[ -f "$MODEL_DIR/config.json" ]] || { echo "modelo ausente: $MODEL_DIR" >&2; exit 66; }
  mkdir -p "$RESULTS" "$LOGS"
  wait_port_free

  local ts boot_log out
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  boot_log="$LOGS/p1-mlxserve-${ver}-${CTX}-boot.log"
  out="$RESULTS/p1-mlxserve-${ver}-${CTX}.jsonl"

  echo ">>> ${ver}: subindo servidor (ctx ${CTX})"
  QWEN38_MLX_SERVE_BIN="$bin" \
  QWEN38_MLX_MODEL_DIR="$MODEL_DIR" \
  QWEN38_CTX_SIZE="$CTX" \
    nohup bash "$HARNESS/run-mlx-serve.sh" FS >"$boot_log" 2>&1 &
  SERVER_PID=$!

  local ready=""
  for _ in $(seq 1 120); do
    server_ready && { ready=1; break; }
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "servidor morreu no boot; ver $boot_log" >&2; exit 69; }
    sleep 3
  done
  [[ -n "$ready" ]] || { echo "servidor ${ver} nao ficou pronto; ver $boot_log" >&2; exit 69; }

  local model_id
  model_id="$(curl -s "$BASE/v1/models" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])')"
  echo ">>> ${ver}: pronto. model_id=${model_id}. rodando cache_probe -> $out"

  python3 "$HARNESS/cache_probe.py" \
    --base-url "$BASE/v1" \
    --model "$model_id" --api-model "$model_id" \
    --runtime mlx-serve --runtime-revision "$ver" \
    --model-revision "$MODEL_REV" \
    --arm FS --session-id "${ts}-FS-${CTX}-${ver}" \
    --context "$CTX" --content-class audit_retrieval --repeat 3 \
    --output "$out" \
    --metrics-url "$BASE/metrics" \
    --cache-enabled --mtp-enabled

  kill "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
  wait_port_free
  echo ">>> ${ver}: OK -> $out"
}

case "$VER" in
  both) run_one v26.9.1; run_one v26.9.2 ;;
  *)    run_one "$VER" ;;
esac
