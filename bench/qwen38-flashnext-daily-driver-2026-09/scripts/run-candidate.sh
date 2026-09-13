#!/usr/bin/env bash
# Driver unico da campanha flashnext-daily-driver: sobe UM candidato, roda o cache_probe com o
# perfil do vendor, amostra memoria e derruba o servidor. Um candidato por vez.
#   c1 = ddalcu mixed-4/8 @ mlx-serve 26.9.2      c2 = Jundot oQ4e @ oMLX 0.6.4
#   c3 = Jundot oQ4e @ oMLX 0.7.0.dev2            c4 = MTPLX Optimized-Speed @ MTPLX 2.11.2
set -euo pipefail

CAND="${1:?uso: $0 <c1|c2|c3|c4> <ctx> [--scenarios a,b] [--repeat N] [--temperature T] [--tag X] [--yarn F] [--generation-mode M] [--print]}"
CTX="${2:?ctx obrigatorio}"; shift 2
SCENARIOS=""; REPEAT=1; TEMP=1.0; TAG=""; YARN=""; GENMODE=""; PRINT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenarios) SCENARIOS="$2"; shift 2 ;;
    --repeat) REPEAT="$2"; shift 2 ;;
    --temperature) TEMP="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --yarn) YARN="$2"; shift 2 ;;
    --generation-mode) GENMODE="$2"; shift 2 ;;
    --print) PRINT=1; shift ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
HERE="$REPO/bench/qwen38-flashnext-daily-driver-2026-09"
RESULTS="$HERE/results"; LOGS="$HERE/logs"
MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache"
DDALCU="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
OQ4E="$MODEL_ROOT/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
MTPLXPACK="$MODEL_ROOT/Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"

# Por candidato: launcher, arm, porta, binario, python do probe, tokenizer, metrics.
case "$CAND" in
  c1) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.9.2
      MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve
      # mlx-serve /metrics exposes no MTP counter (acceptance comes from the
      # server log via attach_mtp), so skip it entirely and avoid the
      # intermittent connection-reset race on that endpoint.
      METRICS=""
      export QWEN38_MLX_SERVE_BIN="$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve"
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="v26.9.2-yarn${YARN}-kv8"
      fi ;;
  c2|c3)
      LAUNCHER="$HARNESS/run-omlx.sh"; ARM=FN; PORT=8000; RUNTIME=omlx
      MODEL_DIR="$OQ4E"; MODEL_REV=2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      if [[ "$CAND" == c2 ]]; then
        REV=v0.6.4; PROBE_PY="$HOME/.local/share/uv/tools/omlx/bin/python"
        export QWEN38_OMLX_BIN="$HOME/.local/share/uv/tools/omlx/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.6.4
      else
        REV=v0.7.0.dev2; PROBE_PY="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/python"
        export QWEN38_OMLX_BIN="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2
      fi ;;
  c4) LAUNCHER="$HARNESS/run-mtplx.sh"; ARM=FX; PORT=8000; RUNTIME=MTPLX; REV=v2.11.2
      MODEL_DIR="$MTPLXPACK"; MODEL_REV=6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6
      PROBE_PY="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/python"; TOKENIZER="$MODEL_DIR"
      METRICS="http://127.0.0.1:$PORT/metrics"; SERVER_NAME=mtplx
      export QWEN38_MTPLX_BIN="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx" QWEN38_MTPLX_EXPECTED_VERSION=2.11.2
      export QWEN38_CTX_SIZE="$CTX"
      [[ -n "$GENMODE" ]] && export QWEN38_MTPLX_GENERATION_MODE="$GENMODE"
      [[ -n "$GENMODE" && "$GENMODE" != mtp ]] && REV="v2.11.2-${GENMODE}" ;;
  *) echo "candidato desconhecido: $CAND" >&2; exit 64 ;;
esac
export QWEN38_MODEL_ROOT="$MODEL_ROOT"
BASE="http://127.0.0.1:$PORT"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
NAME="${CAND}-${CTX}-t${TEMP}${TAG:+-$TAG}"
OUT="$RESULTS/$NAME.jsonl"; BOOT="$LOGS/$NAME-boot.log"; MEM="$LOGS/$NAME-mem.jsonl"

if [[ -n "$PRINT" ]]; then
  echo "launcher: $LAUNCHER $ARM"; bash "$LAUNCHER" "$ARM" --print; echo
  echo "probe: $PROBE_PY cache_probe.py --base-url $BASE/v1 --runtime $RUNTIME --runtime-revision $REV --context $CTX --repeat $REPEAT --temperature $TEMP ${SCENARIOS:+--scenarios $SCENARIOS} ${TOKENIZER:+--tokenizer-path $TOKENIZER} ${METRICS:+--metrics-url $METRICS}"
  echo "saida: $OUT"; exit 0
fi

mkdir -p "$RESULTS" "$LOGS"
SERVER_PID=""; SAMPLER_PID=""
cleanup() {
  [[ -n "$SAMPLER_PID" ]] && kill "$SAMPLER_PID" 2>/dev/null || true
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

wait_port_free() { for _ in $(seq 1 30); do lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || return 0; sleep 1; done; echo "porta $PORT nao liberou" >&2; return 1; }
wait_mem_free() {
  local need="${1:-82}" free
  for _ in $(seq 1 24); do
    free="$(python3 -c 'import re,subprocess;o=subprocess.check_output(["vm_stat"]).decode();ps=int(re.search(r"page size of (\d+)",o).group(1));m=re.search(r"Pages free:\s+(\d+)\.",o);print(int(m.group(1))*ps/1e9)')"
    awk "BEGIN{exit !($free >= $need)}" && { echo "    memoria livre ~${free} GB (>= $need)"; return 0; }
    sleep 5
  done
  echo "    aviso: memoria nao assentou em 120s; seguindo" >&2
}
server_ready() { curl -fsS --max-time 3 "$BASE/v1/models" >/dev/null 2>&1; }

wait_port_free; wait_mem_free 82
# cold tem que ser frio: o disco de prefix-cache do mlx-serve persiste entre restarts (rodada 1 do P1
# foi descartada por isso). oMLX e MTPLX gravam sob logs/<run-id>, novo a cada subida.
if [[ -d "$HOME/.mlx-serve/kv-cache" ]]; then echo "    limpando ~/.mlx-serve/kv-cache"; rm -rf "$HOME/.mlx-serve/kv-cache/"* 2>/dev/null || true; fi

echo ">>> $NAME: sampler + servidor ($LAUNCHER $ARM)"
bash "$HERE/scripts/mem-sampler.sh" "$MEM" "$SERVER_NAME" 5 & SAMPLER_PID=$!
nohup bash "$LAUNCHER" "$ARM" >"$BOOT" 2>&1 & SERVER_PID=$!
ready=""
for _ in $(seq 1 200); do
  server_ready && { ready=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "servidor morreu no boot; ver $BOOT" >&2; exit 69; }
  sleep 3
done
[[ -n "$ready" ]] || { echo "servidor nao ficou pronto em 10 min; ver $BOOT" >&2; exit 69; }
MODEL_ID="$(curl -fsS "$BASE/v1/models" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])')"
echo ">>> $NAME: pronto. model_id=$MODEL_ID -> $OUT"

"$PROBE_PY" "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" --model "$MODEL_ID" --api-model "$MODEL_ID" \
  --runtime "$RUNTIME" --runtime-revision "$REV" --model-revision "$MODEL_REV" \
  --arm "$CAND" --session-id "${TS}-${NAME}" \
  --context "$CTX" --content-class audit_retrieval --repeat "$REPEAT" \
  --temperature "$TEMP" --top-p 0.95 --top-k 20 --reasoning-effort xhigh \
  ${SCENARIOS:+--scenarios "$SCENARIOS"} \
  ${TOKENIZER:+--tokenizer-path "$TOKENIZER"} \
  ${METRICS:+--metrics-url "$METRICS"} \
  --output "$OUT" --cache-enabled $([[ "$GENMODE" == "" || "$GENMODE" == mtp ]] && echo --mtp-enabled)

kill "$SAMPLER_PID" 2>/dev/null || true; SAMPLER_PID=""
python3 "$HERE/scripts/attach_memory.py" --results "$OUT" --sampler "$MEM"
python3 "$HERE/scripts/attach_mtp.py" --results "$OUT" --log "$BOOT" || true
kill "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""; wait_port_free
echo ">>> $NAME: OK"
