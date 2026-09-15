#!/usr/bin/env bash
# P1 item 2 — A/B de runtime do MTPLX no 27B (arm V, Optimized-Speed): 2.11.1 vs 2.11.2.
# Isola so o binario. A SessionBank do MTPLX e em RAM; reiniciar o servidor a limpa,
# entao nao ha cache de disco persistente para higienizar (diferente do mlx-serve).
#
# Uso: run-p2-mtplx-ab.sh <v2.11.1|v2.11.2|both> [ctx]
set -euo pipefail

VER="${1:-}"
CTX="${2:-32768}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
RESULTS="$REPO/bench/qwen38-updates-2026-09/results"
LOGS="$REPO/bench/qwen38-updates-2026-09/logs"

MODEL_REV="123db8bcc7101455b00d9aad36c0e760c6e7de02"
MODEL_DIR="$HOME/.cache/local-llms/qwen3.8-prefix-cache/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-$MODEL_REV"
PORT=8000
BASE="http://127.0.0.1:${PORT}"

case "$VER" in
  v2.11.1|v2.11.2|both) ;;
  *) echo "uso: $0 <v2.11.1|v2.11.2|both> [ctx]" >&2; exit 64 ;;
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

server_ready() { curl -fsS --max-time 3 "$BASE/v1/models" >/dev/null 2>&1; }

run_one() {
  local ver="$1"
  local bin="$HOME/.local/opt/qwen38/mtplx-${ver}/bin/mtplx"
  local bin_python="$HOME/.local/opt/qwen38/mtplx-${ver}/bin/python"
  [[ -x "$bin" ]] || { echo "binario ausente: $bin" >&2; exit 66; }
  [[ -x "$bin_python" ]] || { echo "python do venv ausente: $bin_python" >&2; exit 66; }
  mkdir -p "$RESULTS" "$LOGS"
  wait_port_free

  local ts boot_log out expected
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  expected="${ver#v}"
  boot_log="$LOGS/p2-mtplx-${ver}-${CTX}-boot.log"
  out="$RESULTS/p2-mtplx-${ver}-${CTX}.jsonl"

  echo ">>> ${ver}: subindo MTPLX (arm V, ctx ${CTX})"
  QWEN38_MTPLX_BIN="$bin" \
  QWEN38_MTPLX_EXPECTED_VERSION="$expected" \
  QWEN38_CTX_SIZE="$CTX" \
    nohup bash "$HARNESS/run-mtplx.sh" V >"$boot_log" 2>&1 &
  SERVER_PID=$!

  local ready=""
  for _ in $(seq 1 90); do
    server_ready && { ready=1; break; }
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "MTPLX morreu no boot; ver $boot_log" >&2; exit 69; }
    sleep 3
  done
  [[ -n "$ready" ]] || { echo "MTPLX ${ver} nao ficou pronto; ver $boot_log" >&2; exit 69; }

  local model_id
  model_id="$(curl -fsS "$BASE/v1/models" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null || true)"
  [[ -n "$model_id" ]] || { echo "nao consegui o model_id de /v1/models" >&2; exit 69; }
  echo ">>> ${ver}: pronto. model_id=${model_id}. rodando cache_probe -> $out"

  # MTPLX nao expoe /tokenize; usa tokenizer local. O python do venv MTPLX tem transformers.
  "$bin_python" "$HARNESS/cache_probe.py" \
    --base-url "$BASE/v1" \
    --model "$model_id" --api-model "$model_id" \
    --runtime mtplx --runtime-revision "$ver" \
    --model-revision "$MODEL_REV" \
    --tokenizer-path "$MODEL_DIR" \
    --arm V --session-id "${ts}-V-${CTX}-${ver}" \
    --context "$CTX" --content-class audit_retrieval --repeat 3 \
    --output "$out" \
    --cache-enabled --mtp-enabled

  kill "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
  wait_port_free
  echo ">>> ${ver}: OK -> $out"
}

case "$VER" in
  both) run_one v2.11.1; run_one v2.11.2 ;;
  *)    run_one "$VER" ;;
esac
