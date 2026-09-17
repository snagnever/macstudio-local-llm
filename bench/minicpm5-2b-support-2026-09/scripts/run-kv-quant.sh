#!/usr/bin/env bash
# Efeito da quantizacao de KV do modelo de suporte (s1), com contexto ate 128K.
#
# Fase 1 (solo): s1 com KV fp16 e com KV 8-bit, prompts de ~400, ~8K e ~128K,
#   medindo TTFT/decode e memoria. A 128K o KV do s1 deixa de ser desprezivel
#   (~5,4 GB fp16 vs ~2,7 GB em 8-bit).
# Fase 2 (concorrencia): arranjo B (driver + s1) a 128K com o suporte em KV 8-bit,
#   para comparar com o B@128K fp16 (16,49 s, +31,1%).
#
# uso: screen -dmS mcp5kv bash -lc "bash scripts/run-kv-quant.sh"
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs/kv-quant.log"
LOAD="$HERE/scripts/support-load.py"
SERVE="$HERE/scripts/serve-support.sh"
mkdir -p "$HERE/logs" "$HERE/results"

mem_snapshot() {
  python3 -c '
import re, subprocess
o = subprocess.check_output(["vm_stat"]).decode()
ps = int(re.search(r"page size of (\d+)", o).group(1))
def pages(l):
    m = re.search(l + r":\s+(\d+)\.", o); return int(m.group(1)) * ps / 1e9
swap = subprocess.check_output(["sysctl", "-n", "vm.swapusage"]).decode()
used = re.search(r"used = ([\d.]+)M", swap)
print("wired_gb=%.2f free_gb=%.2f swap_used_gb=%.2f" % (
    pages("Pages wired down"), pages("Pages free"),
    float(used.group(1)) / 1024 if used else 0.0))
' 2>/dev/null || true
}

solo_mode() {
  local mode="$1" kvbits="$2"
  local boot="$HERE/logs/kv-s1-$mode-boot.log"
  local out="$HERE/results/etapa-kv-s1-$mode.jsonl"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] solo mode=$mode kvbits=${kvbits:-off}" >>"$LOG"
  [[ -s "$out" ]] && mv "$out" "$out.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  if [[ -n "$kvbits" ]]; then
    SUPPORT_KV_BITS="$kvbits" nohup bash "$SERVE" s1 >"$boot" 2>&1 &
  else
    nohup bash "$SERVE" s1 >"$boot" 2>&1 &
  fi
  local sp=$!
  for _ in $(seq 1 60); do curl -fsS --max-time 3 http://127.0.0.1:11235/v1/models >/dev/null 2>&1 && break; sleep 1; done
  grep -h "KV" "$boot" | head -1 >>"$LOG" || true
  local M
  M="$(curl -fsS http://127.0.0.1:11235/v1/models | python3 -c 'import sys,json;ids=[m["id"] for m in json.load(sys.stdin)["data"]];print(next((i for i in ids if i.endswith(":no-think")), ids[0]))')"
  python3 "$LOAD" --base-url http://127.0.0.1:11235/v1 --model "$M" --warmup \
    --duration 15 --prompt-tokens 400 --max-tokens 256 --output "$out" >/dev/null 2>&1
  python3 "$LOAD" --base-url http://127.0.0.1:11235/v1 --model "$M" --warmup \
    --duration 20 --prompt-tokens 8000 --max-tokens 256 --output "$out" >/dev/null 2>&1
  python3 "$LOAD" --base-url http://127.0.0.1:11235/v1 --model "$M" \
    --turns 4 --duration 3600 --prompt-tokens 120000 --max-tokens 128 --output "$out" >/dev/null 2>&1
  local pid; pid="$(pgrep -f "optiq serve --model .*MiniCPM5" | head -1)"
  { echo -n "    server_rss_gb=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{printf "%.2f", $1/1048576}') "; mem_snapshot; } >>"$LOG"
  kill "$sp" 2>/dev/null || true
  pkill -f "optiq serve --model .*MiniCPM5" 2>/dev/null || true
  for _ in $(seq 1 30); do lsof -nP -iTCP:11235 -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 1; done
}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] kv-quant begin" >>"$LOG"
solo_mode fp16 ""
solo_mode kv8 8

# Fase 2: concorrencia a 128K com o suporte em KV 8-bit.
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] concorrencia B@128K kv8" >>"$LOG"
SUPPORT_KV_BITS=8 bash "$HERE/scripts/run-arrangement.sh" B 131072 \
  --repeat 1 --restart-driver --tag kv8 >>"$LOG" 2>&1
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] KVDONE" >>"$LOG"