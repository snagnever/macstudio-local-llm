#!/usr/bin/env bash
# P4c — Flash-Next no ds4-server (fork ivanfioravanti/ds4 branch qwen3.8-flash-next).
# ds4-server serve OpenAI /v1, entao o cache_probe funciona. Requisitos do ds4:
#   - rodar com cwd no repo do fork (compila metal/*.metal em runtime);
#   - --ple aponta o sidecar PLE (base gguf nao tem n-gram inline);
#   - sem /tokenize -> cache_probe usa --tokenizer-path (tokenizer do FN em disco).
# Nao e A/B: compara com os numeros ja medidos do mlx-serve 26.9.2 mixed-4/8.
#
# Uso: run-p4c-ds4server-flashnext.sh <ctx>
set -uo pipefail

CTX="${1:?uso: $0 <ctx>}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
RESULTS="$REPO/bench/qwen38-updates-2026-09/results"
LOGS="$REPO/bench/qwen38-updates-2026-09/logs"

DS4_REPO="$HOME/.local/opt/qwen38/ds4-fork"
D="$HOME/.cache/local-llms/qwen3.8-prefix-cache/ivanfioravanti-Qwen3.8-Flash-Next-DS4-Q4-3e95a639e7f8ee791e43272b39d322a185b193c7"
BASE_GGUF="$D/Qwen3.8-Flash-Next-Q4KImatrixExperts-MXFP4Down-BF16Emb-BF16Control-Q8GDN-Q8QSA-Q8Shared-Q8Out-MTP.gguf"
PLE="$D/Qwen3.8-Flash-Next-PLE-Q4_1.gguf"
TOKENIZER="$HOME/.cache/local-llms/qwen3.8-prefix-cache/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
PYBIN="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/python"   # tem transformers
PORT=11234
BASE="http://127.0.0.1:${PORT}"
MODEL_REV="3e95a639e7f8ee791e43272b39d322a185b193c7"

for f in "$BASE_GGUF" "$PLE" "$DS4_REPO/ds4-server" "$PYBIN"; do
  [[ -e "$f" ]] || { echo "faltando: $f" >&2; exit 66; }
done
mkdir -p "$RESULTS" "$LOGS"

SERVER_PID=""
cleanup() { [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT

for _ in $(seq 1 30); do lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done

ts="$(date -u +%Y%m%dT%H%M%SZ)"
boot_log="$LOGS/p4c-ds4server-${CTX}-boot.log"
out="$RESULTS/p4c-ds4server-flashnext-${CTX}.jsonl"

echo ">>> ds4-server: subindo (ctx ${CTX}, cwd=repo p/ shaders Metal)"
( cd "$DS4_REPO" && exec ./ds4-server -m "$BASE_GGUF" --ple "$PLE" --metal \
    -c "$CTX" --prefill-chunk 1024 --host 0.0.0.0 --port "$PORT" ) >"$boot_log" 2>&1 &
SERVER_PID=$!

ready=""
for _ in $(seq 1 160); do
  curl -fsS --max-time 3 "$BASE/v1/models" >/dev/null 2>&1 && { ready=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "ds4-server morreu no boot; ver $boot_log" >&2; exit 69; }
  sleep 3
done
[[ -n "$ready" ]] || { echo "ds4-server nao ficou pronto; ver $boot_log" >&2; exit 69; }

model_id="$(curl -fsS "$BASE/v1/models" | "$PYBIN" -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])')"
echo ">>> ds4-server: pronto. model_id=${model_id}. cache_probe -> $out"

"$PYBIN" "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" \
  --model "$model_id" --api-model "$model_id" \
  --runtime ds4 --runtime-revision "ds4-fork/qwen3.8-flash-next" \
  --model-revision "$MODEL_REV" \
  --tokenizer-path "$TOKENIZER" \
  --arm FS --session-id "${ts}-ds4srv-${CTX}" \
  --context "$CTX" --content-class audit_retrieval --repeat "${P1_REPEAT:-3}" \
  ${P1_SCENARIOS:+--scenarios "$P1_SCENARIOS"} \
  --output "$out" \
  --cache-enabled --mtp-enabled

kill "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
echo ">>> ds4-server: OK -> $out"
