#!/usr/bin/env bash
# UD-Q2_K_XL Task 5 — LCB v6 full 50. Some cases blow to 11k tok / ~19 min; expect 6-12h.
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-udq2kxl-lcb.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
DRIVER=$LOGDIR/udq2kxl-lcb-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "LCB START"
FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: ${FREE_GB}GB free"; exit 1; }
curl -sf http://127.0.0.1:1235/health >/dev/null || { say "ABORT: server down"; exit 1; }
cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
export BENCH_TIMEOUT=3600
"$ROOT/.venv/bin/python" scripts/bench2.py livecodebench --examples 50 \
  --model deepseek-v4-flash-udq2kxl --lcb-version release_v6 --max-tokens 32768 \
  > "$LOGDIR/udq2kxl-lcb.log" 2>&1
say "LCB rc=$?"
