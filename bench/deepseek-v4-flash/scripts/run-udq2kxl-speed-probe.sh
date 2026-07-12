#!/usr/bin/env bash
# UD-Q2_K_XL campaign Task 1 — preflight + 3-question speed probe (thinking off).
# Usage: bash bench/deepseek-v4-flash/scripts/run-udq2kxl-speed-probe.sh
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/udq2kxl-speed-probe-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

# --- disk preflight (2026-07-12 incident rule) ---
FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: only ${FREE_GB}GB free (<150)"; exit 1; }
say "disk ok: ${FREE_GB}GB free"

# --- sole-model preflight ---
pgrep -f mlx_lm.server >/dev/null && { say "ABORT: mlx_lm.server running"; exit 1; }
/Users/vitor/.lmstudio/bin/lms ps 2>/dev/null | grep -q . && { say "ABORT: LM Studio has a model loaded"; exit 1; }

# --- server up (reuse if already healthy with right alias) ---
if ! curl -sf http://127.0.0.1:1235/health >/dev/null 2>&1; then
  BIN=~/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.24.0
  M=~/.lmstudio/models/unsloth/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-UD-Q2_K_XL-00001-of-00003.gguf
  SRVLOG=$LOGDIR/udq2kxl-server.log
  ( cd "$BIN" && nohup ./llama-server -m "$M" -a deepseek-v4-flash-udq2kxl \
      --no-repack -c 32768 -np 1 -ngl 999 --host 127.0.0.1 --port 1235 \
      > "$SRVLOG" 2>&1 & disown )
  for i in $(seq 1 120); do
    curl -sf http://127.0.0.1:1235/health >/dev/null 2>&1 && break; sleep 5
  done
fi
curl -sf http://127.0.0.1:1235/health >/dev/null || { say "ABORT: server not healthy"; exit 1; }
say "server healthy"

# --- thinking-off verification: one generation, assert 0 reasoning tokens ---
RT=$(curl -s http://127.0.0.1:1235/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash-udq2kxl","messages":[{"role":"user","content":"Why is the sky blue? One sentence."}],"max_tokens":128,"temperature":0}' \
  | /Users/vitor/LocalProjects/local-llms/.venv/bin/python -c \
  "import json,sys; d=json.load(sys.stdin); u=d.get('usage',{}); print(u.get('completion_tokens_details',{}).get('reasoning_tokens',0)); print(d['choices'][0]['message']['content'][:100],file=sys.stderr)")
say "reasoning_tokens=$RT (must be 0)"
[ "$RT" = "0" ] || say "WARNING: nonzero reasoning tokens — investigate before benching"

# --- 3-question speed probe ---
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
cd "$ROOT/tools/local-llm-bench-m4-32gb"
"$ROOT/.venv/bin/python" scripts/speed_probe.py deepseek-v4-flash-udq2kxl results/speed_probe \
  2>&1 | tee -a "$DRIVER"
say "speed probe done — results in tools/local-llm-bench-m4-32gb/results/speed_probe/"
