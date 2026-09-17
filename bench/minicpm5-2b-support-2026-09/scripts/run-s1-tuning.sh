#!/usr/bin/env bash
# Tuning do s1: n-gram, saida guiada, KV misto e efeito no driver. Ver plan-tuning.md.
# uso: screen -dmS mcp5tune bash -lc "bash scripts/run-s1-tuning.sh"
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs/tuning.log"
LOAD="$HERE/scripts/support-load.py"
SERVE="$HERE/scripts/serve-support.sh"
Q="$HERE/scripts/quality-run.py"
TASKS="$HERE/scripts/quality-tasks.json"
MODEL="$HOME/.cache/local-llms/minicpm5-2b-support/mlx-community-MiniCPM5-2B-OptiQ-4bit-d1392929adb5693640daeebe6b45e12a07a60b5a"
KVCONF="$MODEL/kv_config.json"
mkdir -p "$HERE/logs" "$HERE/results"

snap() {
  python3 -c '
import re, subprocess
o = subprocess.check_output(["vm_stat"]).decode()
ps = int(re.search(r"page size of (\d+)", o).group(1))
def pages(l):
    m = re.search(l + r":\s+(\d+)\.", o); return int(m.group(1)) * ps / 1e9
print("wired=%.2f free=%.2f" % (pages("Pages wired down"), pages("Pages free")))
' 2>/dev/null
}

start_s1() {  # env vars already exported by caller
  local boot="$HERE/logs/tuning-$1-boot.log"
  nohup bash "$SERVE" s1 >"$boot" 2>&1 &
  for _ in $(seq 1 60); do curl -fsS --max-time 3 http://127.0.0.1:11235/v1/models >/dev/null 2>&1 && break; sleep 1; done
  grep -hE "KV|ngram|ngram-draft" "$boot" | head -2 >>"$LOG" || true
  curl -fsS http://127.0.0.1:11235/v1/models | python3 -c 'import sys,json;ids=[m["id"] for m in json.load(sys.stdin)["data"]];print(next((i for i in ids if i.endswith(":no-think")), ids[0]))'
}

stop_s1() {
  pkill -f "optiq serve --model .*MiniCPM5" 2>/dev/null || true
  for _ in $(seq 1 30); do lsof -nP -iTCP:11235 -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done
}

run_load() {  # $1=out $2=prompt_tokens $3=duration $4=extra
  local out="$HERE/results/$1" pt="$2" dur="$3"; shift 3
  python3 "$LOAD" --base-url http://127.0.0.1:11235/v1 --model "$M" --warmup \
    --duration "$dur" --prompt-tokens "$pt" --max-tokens 256 --output "$out" "$@" >/dev/null 2>&1
}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] tuning begin" >>"$LOG"

# ---- Fase 1: n-gram (base vs ngram-16), generic vs copy-heavy ----
for mode in base ng; do
  unset SUPPORT_NGRAM_DRAFT SUPPORT_KV_CONFIG SUPPORT_KV_BITS
  [[ "$mode" == ng ]] && export SUPPORT_NGRAM_DRAFT=16
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] fase1 mode=$mode $(snap)" >>"$LOG"
  stop_s1; M="$(start_s1 "$mode")"
  run_load "etapa-tuning-$mode-generic.jsonl" 400 15
  run_load "etapa-tuning-$mode-copy.jsonl" 400 15 --copy-heavy
done

# ---- Fase 2: saida guiada na classificacao ----
unset SUPPORT_NGRAM_DRAFT SUPPORT_KV_CONFIG SUPPORT_KV_BITS
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] fase2 guided" >>"$LOG"
stop_s1; M="$(start_s1 guided)"
[[ -s "$HERE/results/etapa-tuning-guided.jsonl" ]] && \
  mv "$HERE/results/etapa-tuning-guided.jsonl" "$HERE/results/etapa-tuning-guided.jsonl.bak"
python3 "$Q" --base-url http://127.0.0.1:11235/v1 --model "$M" --arm s1 \
  --tasks "$TASKS" --guided-classification --output "$HERE/results/etapa-tuning-guided.jsonl" \
  >/dev/null 2>&1

# ---- Fase 3: KV misto vs fp16 a 8K/32K ----
for mode in fp16 kvcfg; do
  unset SUPPORT_NGRAM_DRAFT SUPPORT_KV_CONFIG SUPPORT_KV_BITS
  [[ "$mode" == kvcfg ]] && export SUPPORT_KV_CONFIG="$KVCONF"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] fase3 mode=$mode $(snap)" >>"$LOG"
  stop_s1; M="$(start_s1 "kv-$mode")"
  run_load "etapa-tuning-kv-$mode-8k.jsonl" 8000 15
  run_load "etapa-tuning-kv-$mode-32k.jsonl" 32000 20
done
stop_s1

# ---- Fase 4: efeito no driver (B@32K com ngram no suporte) ----
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] fase4 driver B@32K ngram" >>"$LOG"
SUPPORT_NGRAM_DRAFT=16 bash "$HERE/scripts/run-arrangement.sh" B 32768 \
  --repeat 1 --restart-driver --tag ng >>"$LOG" 2>&1

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] TUNINGDONE" >>"$LOG"