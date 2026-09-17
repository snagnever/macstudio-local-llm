#!/usr/bin/env bash
# Etapa 2 — mede o T_turno do driver sob concorrência com um modelo de suporte.
#
# Arranjos:
#   A  driver sozinho (re-confirma o baseline na sessão de hoje)
#   B  driver + MiniCPM5-2B-OptiQ-4bit  (s1)
#   C  driver + MiniCPM5-2B-8bit        (s2)
#   D  driver + gemma-4-E4B-it-MLX-8bit (s3, incumbente do slot pequeno)
#
# O driver (mlx-serve na 11234) precisa estar no ar: este script NÃO o sobe por
# padrão, para não pagar 3 min de carga a cada arranjo. Se quiser que ele suba o
# driver, passe --start-driver (usa o launcher da campanha do daily-driver).
#
# Enquanto o cache_probe roda contra o driver, o modelo de suporte gera turnos
# curtos em laço (support-load.py). Amostra-se memória/wired/swap durante tudo.
#
# uso: run-arrangement.sh <A|B|C|D> <ctx> [--repeat N] [--load-duration S]
#                          [--scenarios a,b] [--tag X] [--start-driver] [--print]
set -euo pipefail

ARM="${1:?uso: $0 <A|B|C|D> <ctx> [opcoes]}"
CTX="${2:?ctx obrigatorio}"; shift 2

REPEAT=1; LOAD_DUR=3600; LOAD_GAP=0; SCENARIOS=""; TAG=""; START_DRIVER=""; RESTART_DRIVER=""; PRINT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repeat) REPEAT="$2"; shift 2 ;;
    --load-duration) LOAD_DUR="$2"; shift 2 ;;
    --load-gap) LOAD_GAP="$2"; shift 2 ;;
    --scenarios) SCENARIOS="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --start-driver) START_DRIVER=1; shift ;;
    --restart-driver) RESTART_DRIVER=1; shift ;;
    --print) PRINT=1; shift ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
DD="$REPO/bench/qwen38-flashnext-daily-driver-2026-09/scripts"
HERE="$REPO/bench/minicpm5-2b-support-2026-09"
RESULTS="$HERE/results"; LOGS="$HERE/logs"
DRIVER_URL="http://127.0.0.1:11234"
SUPPORT_URL="http://127.0.0.1:11235"
DRIVER_REV="v26.9.2"; DRIVER_MODEL_REV="ef5b919d31534faa1997666f1a22d362cd6383cd"
# Perfil do driver: daily (131072, fp16 KV) ou 512k (524288 com YaRN 2.0 + KV 8-bit).
DRIVER_PROFILE="${DRIVER_PROFILE:-daily}"
[[ "$DRIVER_PROFILE" != "daily" ]] && DRIVER_REV="v26.9.2-$DRIVER_PROFILE"
SUPPORT_LOAD="$HERE/scripts/support-load.py"
PROBE_PY="${PROBE_PY:-python3}"
# Opcional: tokenizer local em vez do endpoint /tokenize do mlx-serve, que
# reseta a conexão de forma intermitente em contexto longo. Exige um python
# com transformers (ex.: ~/.local/share/uv/tools/omlx/bin/python).
TOKENIZER_PATH="${PROBE_TOKENIZER_PATH:-}"

case "$ARM" in
  A) SUPPORT=""; SUPPORT_ARM="" ;;
  B) SUPPORT="s1"; SUPPORT_ARM=s1 ;;
  C) SUPPORT="s2"; SUPPORT_ARM=s2 ;;
  D) SUPPORT="s3"; SUPPORT_ARM=s3 ;;
  *) echo "arranjo desconhecido: $ARM (use A|B|C|D)" >&2; exit 64 ;;
esac

NAME="${ARM}-${CTX}-t1.0${TAG:+-$TAG}"
[[ "${LOAD_GAP%%.*}" -gt 0 ]] 2>/dev/null && NAME="${NAME}-gap${LOAD_GAP}"
OUT="$RESULTS/$NAME.jsonl"; MEM="$LOGS/$NAME-mem.jsonl"; LOADLOG="$LOGS/$NAME-load.jsonl"
BOOT="$LOGS/$NAME-boot.log"; SUPPORT_BOOT="$LOGS/$NAME-support-boot.log"
DRIVER_BOOT="$LOGS/$NAME-driver-boot.log"

SCENARIO_REPEATS=""
[[ "$REPEAT" -gt 1 ]] && SCENARIO_REPEATS="middle_mutation=1"

if [[ -n "$PRINT" ]]; then
  echo "arranjo: $ARM  support=${SUPPORT:-nenhum}  ctx=$CTX  repeat=$REPEAT"
  echo "driver:  $DRIVER_URL  (precisa estar no ar)"
  [[ -n "$SUPPORT" ]] && bash "$HERE/scripts/serve-support.sh" "$SUPPORT_ARM" --print
  echo "probe:   $PROBE_PY $HARNESS/cache_probe.py --base-url $DRIVER_URL/v1 ... --arm $ARM --context $CTX --repeat $REPEAT"
  echo "saida:   $OUT"
  exit 0
fi

mkdir -p "$RESULTS" "$LOGS"

if [[ -n "$START_DRIVER" || -n "$RESTART_DRIVER" ]]; then
  if [[ -n "$RESTART_DRIVER" ]]; then
    echo ">>> $NAME: reiniciando driver (kill + limpar kv-cache)"
    listeners="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN 2>/dev/null || true)"
    [[ -n "$listeners" ]] && kill $listeners 2>/dev/null || true
    for _ in $(seq 1 60); do
      lsof -nP -iTCP:11234 -sTCP:LISTEN >/dev/null 2>&1 || break
      sleep 1
    done
    rm -rf "$HOME/.mlx-serve/kv-cache/"* 2>/dev/null || true
  fi
  if ! lsof -nP -iTCP:11234 -sTCP:LISTEN >/dev/null 2>&1; then
    # Memoria precisa assentar antes de carregar 107 GB de novo. "Pages free"
    # sozinho engana: o macOS deixa os pesos mortos como inactive (reclamavel) e
    # so os evicta sob pressao, entao o numero util e free + inactive. Quem
    # decide mesmo e o gate de swap medido durante a rodada, nao este.
    echo ">>> $NAME: aguardando memoria reclamavel >= 90 GB"
    for _ in $(seq 1 24); do
      free="$(python3 -c 'import re,subprocess;o=subprocess.check_output(["vm_stat"]).decode();ps=int(re.search(r"page size of (\d+)",o).group(1));f=int(re.search(r"Pages free:\s+(\d+)\.",o).group(1));i=int(re.search(r"Pages inactive:\s+(\d+)\.",o).group(1));print((f+i)*ps/1e9)')"
      awk "BEGIN{exit !($free >= 90)}" && { echo "    memoria reclamavel ~${free} GB"; break; }
      sleep 5
    done
    echo ">>> $NAME: subindo driver ($DRIVER_PROFILE)"
    nohup bash "$REPO/tools/scripts/serve-flashnext-daily-driver.sh" "$DRIVER_PROFILE" >"$DRIVER_BOOT" 2>&1 &
    DRIVER_PID=$!
  fi
fi

echo ">>> $NAME: aguardando driver em $DRIVER_URL"
for _ in $(seq 1 200); do
  curl -fsS --max-time 3 "$DRIVER_URL/v1/models" >/dev/null 2>&1 && break
  sleep 3
done
curl -fsS --max-time 3 "$DRIVER_URL/v1/models" >/dev/null 2>&1 || {
  echo "driver nao respondeu em $DRIVER_URL; ver $DRIVER_BOOT" >&2; exit 69; }

MODEL_ID="$(curl -fsS "$DRIVER_URL/v1/models" | python3 -c '
import sys, json
ids = [m["id"] for m in json.load(sys.stdin)["data"]]
print(ids[0] if ids else "")')"
[[ -n "$MODEL_ID" ]] || { echo "driver sem model id" >&2; exit 69; }
echo ">>> $NAME: driver model_id=$MODEL_ID"

SUPPORT_PID=""; LOAD_PID=""; SAMPLER_PID=""; DRIVER_PID=""
cleanup() {
  [[ -n "$LOAD_PID" ]] && kill "$LOAD_PID" 2>/dev/null || true
  [[ -n "$SAMPLER_PID" ]] && kill "$SAMPLER_PID" 2>/dev/null || true
  [[ -n "$SUPPORT_PID" ]] && kill "$SUPPORT_PID" 2>/dev/null || true
  local sl; sl="$(lsof -nP -tiTCP:11235 -sTCP:LISTEN 2>/dev/null || true)"
  [[ -n "$sl" ]] && kill $sl 2>/dev/null || true
  if [[ -n "$START_DRIVER" && -n "$DRIVER_PID" ]]; then
    kill "$DRIVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ -s "$OUT" ]]; then
  BAK="$OUT.bak.$(date -u +%Y%m%dT%H%M%SZ)"; mv "$OUT" "$BAK"
  echo "    OUT pre-existente movido para $BAK"
fi
: > "$MEM"; : > "$LOADLOG"

if [[ -n "$SUPPORT" ]]; then
  echo ">>> $NAME: subindo suporte ($SUPPORT) em $SUPPORT_URL"
  nohup bash "$HERE/scripts/serve-support.sh" "$SUPPORT_ARM" >"$SUPPORT_BOOT" 2>&1 &
  SUPPORT_PID=$!
  for _ in $(seq 1 60); do
    curl -fsS --max-time 3 "$SUPPORT_URL/v1/models" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -fsS --max-time 3 "$SUPPORT_URL/v1/models" >/dev/null 2>&1 || {
    echo "suporte nao respondeu; ver $SUPPORT_BOOT" >&2; exit 69; }
  # Primeiro request carrega o modelo; não medir esse request no solo/qualidade.
  SUPPORT_MODEL="$(curl -fsS "$SUPPORT_URL/v1/models" | python3 -c '
import sys, json
ids = [m["id"] for m in json.load(sys.stdin)["data"]]
print(next((i for i in ids if i.endswith(":no-think")), ids[0] if ids else ""))')"
  echo ">>> $NAME: aquecendo suporte ($SUPPORT_MODEL, carrega o modelo)"
  python3 - "$SUPPORT_URL" "$SUPPORT_MODEL" <<'PY'
import json, sys, urllib.request
url = sys.argv[1].rstrip("/") + "/chat/completions"
body = json.dumps({"model": sys.argv[2],
                   "messages": [{"role": "user", "content": "oi"}],
                   "max_tokens": 4}).encode()
req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
try:
    urllib.request.urlopen(req, timeout=600).read()
except Exception as exc:
    print(f"warmup: {exc}", file=sys.stderr)
PY

  # Carga de fundo: turnos curtos em laço, durante todo o probe.
  echo ">>> $NAME: carga de suporte ($SUPPORT_MODEL) por ate ${LOAD_DUR}s"
  nohup "$PROBE_PY" "$SUPPORT_LOAD" \
    --base-url "$SUPPORT_URL/v1" --model "$SUPPORT_MODEL" \
    --duration "$LOAD_DUR" --prompt-tokens 400 --max-tokens 256 \
    --gap "$LOAD_GAP" \
    --output "$LOADLOG" >/dev/null 2>&1 &
  LOAD_PID=$!
  sleep 2
fi

# Sampler de memoria: wired/free/swap, o gate da campanha.
bash "$DD/mem-sampler.sh" "$MEM" mlx-serve 5 & SAMPLER_PID=$!

echo ">>> $NAME: rodando cache_probe (arm=$ARM ctx=$CTX repeat=$REPEAT)"
PROBE_EXIT=0
"$PROBE_PY" "$HARNESS/cache_probe.py" \
  --base-url "$DRIVER_URL/v1" --model "$MODEL_ID" --api-model "$MODEL_ID" \
  --runtime mlx-serve --runtime-revision "$DRIVER_REV" --model-revision "$DRIVER_MODEL_REV" \
  --arm "$ARM" --session-id "$(date -u +%Y%m%dT%H%M%SZ)-$NAME" \
  --context "$CTX" --content-class audit_retrieval --repeat "$REPEAT" \
  --temperature 1.0 --top-p 0.95 --top-k 20 --reasoning-effort xhigh \
  ${SCENARIOS:+--scenarios "$SCENARIOS"} \
  ${SCENARIO_REPEATS:+--scenario-repeats "$SCENARIO_REPEATS"} \
  ${TOKENIZER_PATH:+--tokenizer-path "$TOKENIZER_PATH"} \
  --output "$OUT" --cache-enabled --mtp-enabled \
  >"$LOGS/$NAME-probe.out" 2>&1 \
  || PROBE_EXIT=$?

kill "$LOAD_PID" 2>/dev/null || true; LOAD_PID=""
kill "$SAMPLER_PID" 2>/dev/null || true; SAMPLER_PID=""
"$PROBE_PY" "$DD/attach_memory.py" --results "$OUT" --sampler "$MEM" || true
if [[ -s "$LOADLOG" ]]; then
  echo ">>> $NAME: turnos do suporte:"
  "$PROBE_PY" "$HERE/scripts/summarize_support.py" "$LOADLOG" | tail -8
fi
if [[ "$PROBE_EXIT" -ne 0 ]]; then
  echo ">>> $NAME: probe saiu $PROBE_EXIT" >&2
else
  echo ">>> $NAME: OK"
fi
exit "$PROBE_EXIT"