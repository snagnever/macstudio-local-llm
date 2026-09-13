#!/usr/bin/env bash
# mlx-serve 26.9.2 Flash-Next (mixed-4/8) ACIMA do contexto nativo (262144), via YaRN.
# --config-overrides estende rope. Usa /tokenize do proprio mlx-serve (sem tokenizer-path).
#
# Uso: run-p1-mlxserve-extended.sh <ctx> <yarn_factor>
#   ex.: 524288 2.0  |  786432 3.0  |  1048576 4.0
# Env: P1_SCENARIOS (lista), P1_REPEAT (default 1 aqui — contexto enorme e caro).
set -uo pipefail

CTX="${1:?uso: $0 <ctx> <yarn_factor>}"
FACTOR="${2:?uso: $0 <ctx> <yarn_factor>}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
RESULTS="$REPO/bench/qwen38-updates-2026-09/results"
LOGS="$REPO/bench/qwen38-updates-2026-09/logs"

MODEL="$HOME/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
MODEL_REV="ef5b919d31534faa1997666f1a22d362cd6383cd"
MLX_BIN="${QWEN38_MLX_SERVE_BIN:-$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve}"
PORT=11234
BASE="http://127.0.0.1:${PORT}"
OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${FACTOR},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"

[[ -f "$MODEL/config.json" ]] || { echo "modelo ausente: $MODEL" >&2; exit 66; }
mkdir -p "$RESULTS" "$LOGS"

SERVER_PID=""
cleanup(){ [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT
for _ in $(seq 1 30); do lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done

ts="$(date -u +%Y%m%dT%H%M%SZ)"
boot_log="$LOGS/p1-ext-${CTX}-boot.log"
out="$RESULTS/p1-mlxserve-ext-${CTX}-yarn${FACTOR}.jsonl"

echo ">>> mlx-serve 26.9.2 YaRN: ctx ${CTX} factor ${FACTOR}"
# kv-quant 8 e prefill-chunk menores ajudam a caber KV/working set em contexto enorme
nohup "$MLX_BIN" --model "$MODEL" --serve --host 0.0.0.0 --port "$PORT" \
  --ctx-size "$CTX" --kv-quant 8 --mtp --metrics \
  --prefix-cache-mem 16GB --prefix-cache-disk 100GB --prefix-cache-entries 8 \
  --config-overrides "$OVERRIDES" >"$boot_log" 2>&1 &
SERVER_PID=$!

ready=""
for _ in $(seq 1 240); do
  curl -fsS --max-time 3 "$BASE/v1/models" 2>/dev/null | grep -q '"state": *"ready"' && { ready=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "servidor morreu no boot; ver $boot_log" >&2; exit 69; }
  sleep 5
done
[[ -n "$ready" ]] || { echo "nao ficou pronto; ver $boot_log" >&2; exit 69; }

model_id="$(curl -fsS "$BASE/v1/models" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])')"
echo ">>> pronto. model_id=${model_id}. cache_probe -> $out"

python3 "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" \
  --model "$model_id" --api-model "$model_id" \
  --runtime mlx-serve --runtime-revision "v26.9.2-yarn${FACTOR}" \
  --model-revision "$MODEL_REV" \
  --arm FS --session-id "${ts}-ext-${CTX}" \
  --context "$CTX" --content-class audit_retrieval --repeat "${P1_REPEAT:-1}" \
  ${P1_SCENARIOS:+--scenarios "$P1_SCENARIOS"} \
  --output "$out" \
  --metrics-url "$BASE/metrics" \
  --cache-enabled --mtp-enabled

kill "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
echo ">>> ext ${CTX}: OK -> $out"
