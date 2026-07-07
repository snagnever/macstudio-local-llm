#!/usr/bin/env bash
set -u
LOG=/tmp/ds4_lcb_overnight.log
exec > "$LOG" 2>&1
echo "=== overnight LCB driver armed $(date -Iseconds) ==="

# --- sleep until next 01:00 local ---
target=$(date -v1H -v0M -v0S +%s)
now=$(date +%s)
[ "$target" -le "$now" ] && target=$(date -v+1d -v1H -v0M -v0S +%s)
echo "now=$(date), target=$(date -r "$target"), sleeping $(( (target-now)/60 )) min"
sleep $(( target - now ))

echo "=== waking $(date -Iseconds): starting llama-server ==="
BIN=~/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.24.0
M=~/.lmstudio/models/teamblobfish/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-IQ2_XS-XL-00001-of-00002.gguf
SRVLOG=/tmp/ds4_lcb_overnight_server.log
cd "$BIN" || { echo "ABORT: bin dir missing"; exit 1; }
nohup ./llama-server -m "$M" -a deepseek-v4-flash-iq2xs --no-repack -c 32768 -np 1 -ngl 999 \
  --host 127.0.0.1 --port 1235 > "$SRVLOG" 2>&1 &
SRV=$!
ready=0
for i in $(seq 1 60); do
  grep -qiE 'listening on http' "$SRVLOG" 2>/dev/null && { ready=1; break; }
  kill -0 "$SRV" 2>/dev/null || break
  sleep 3
done
[ "$ready" = 1 ] || { echo "ABORT: server failed to start"; tail -5 "$SRVLOG"; exit 1; }

echo "=== server up, running FULL LCB v6 (50) $(date -Iseconds) ==="
REPO=/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
cd "$REPO"
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
export BENCH_TIMEOUT=3600
.venv/bin/python scripts/bench2.py livecodebench --examples 50 \
  --model deepseek-v4-flash-iq2xs --lcb-version release_v6 --max-tokens 32768
RC=$?
echo "=== LCB finished rc=$RC $(date -Iseconds); stopping server ==="
kill "$SRV" 2>/dev/null
echo "=== OVERNIGHT LCB COMPLETE $(date -Iseconds) ==="
