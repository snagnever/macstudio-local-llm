#!/usr/bin/env bash
# P4b — Flash-Next no motor ds4 embutido do mlx-serve (build ivanfioravanti DS4-Q4).
# Nao e A/B: mede o ds4 num contexto e compara com os numeros ja medidos do mlx-serve
# 26.9.2 (build mixed-4/8, engine MLX nativo). GGUF base + sidecar PLE ao lado.
#
# Uso: run-p4b-ds4-flashnext.sh <ctx>   (ex.: 32768 | 131072 | 262144)
set -euo pipefail

CTX="${1:?uso: $0 <ctx>}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
RESULTS="$REPO/bench/qwen38-updates-2026-09/results"
LOGS="$REPO/bench/qwen38-updates-2026-09/logs"

DS4_DIR="$HOME/.cache/local-llms/qwen3.8-prefix-cache/ivanfioravanti-Qwen3.8-Flash-Next-DS4-Q4-3e95a639e7f8ee791e43272b39d322a185b193c7"
MODEL="$DS4_DIR/Qwen3.8-Flash-Next-Q4KImatrixExperts-MXFP4Down-BF16Emb-BF16Control-Q8GDN-Q8QSA-Q8Shared-Q8Out-MTP.gguf"
MODEL_REV="3e95a639e7f8ee791e43272b39d322a185b193c7"
MLX_BIN="${QWEN38_MLX_SERVE_BIN:-$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve}"
PORT=11234
BASE="http://127.0.0.1:${PORT}"

[[ -f "$MODEL" ]] || { echo "gguf base ausente: $MODEL" >&2; exit 66; }
[[ -f "$DS4_DIR/Qwen3.8-Flash-Next-PLE-Q4_1.gguf" ]] || { echo "sidecar PLE ausente" >&2; exit 66; }
mkdir -p "$RESULTS" "$LOGS"

SERVER_PID=""
cleanup() { [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 30); do lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done

ts="$(date -u +%Y%m%dT%H%M%SZ)"
boot_log="$LOGS/p4b-ds4-${CTX}-boot.log"
out="$RESULTS/p4b-ds4-flashnext-${CTX}.jsonl"

echo ">>> ds4: subindo (engine ds4, --mtp, ctx ${CTX})"
nohup "$MLX_BIN" --model "$MODEL" --engine ds4 --serve --host 0.0.0.0 --port "$PORT" \
  --ctx-size "$CTX" --mtp --metrics >"$boot_log" 2>&1 &
SERVER_PID=$!

ready=""
for _ in $(seq 1 160); do
  curl -fsS --max-time 3 "$BASE/v1/models" 2>/dev/null | grep -q '"state": *"ready"' && { ready=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "servidor morreu no boot; ver $boot_log" >&2; exit 69; }
  sleep 3
done
[[ -n "$ready" ]] || { echo "ds4 nao ficou pronto; ver $boot_log" >&2; exit 69; }

model_id="$(curl -fsS "$BASE/v1/models" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])')"
echo ">>> ds4: pronto. model_id=${model_id}. rodando cache_probe -> $out"

python3 "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" \
  --model "$model_id" --api-model "$model_id" \
  --runtime ds4 --runtime-revision "mlx-serve-26.9.2/ds4" \
  --model-revision "$MODEL_REV" \
  --arm FS --session-id "${ts}-ds4-${CTX}" \
  --context "$CTX" --content-class audit_retrieval --repeat 3 \
  --output "$out" \
  --metrics-url "$BASE/metrics" \
  --cache-enabled --mtp-enabled

kill "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
echo ">>> ds4: OK -> $out"
