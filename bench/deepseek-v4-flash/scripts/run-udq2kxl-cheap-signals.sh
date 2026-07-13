#!/usr/bin/env bash
# UD-Q2_K_XL Task 3 — jdhodges (40) -> Veerman (12) -> HumanEval (100), sequential.
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-udq2kxl-cheap-signals.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
DRIVER=$LOGDIR/udq2kxl-cheap-signals-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "cheap-signals START"

FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: ${FREE_GB}GB free"; exit 1; }
curl -sf http://127.0.0.1:1235/health >/dev/null || { say "ABORT: server down"; exit 1; }

PY=$ROOT/.venv/bin/python
cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
export BENCH_TIMEOUT=3600

say "jdhodges START"
"$PY" scripts/tool_call_bench.py --model deepseek-v4-flash-udq2kxl --suite jdhodges \
  --base-url http://127.0.0.1:1235/v1 --force > "$LOGDIR/udq2kxl-toolcall-jdhodges.log" 2>&1
say "jdhodges rc=$?"

say "veerman START"
"$PY" scripts/tool_call_bench.py --model deepseek-v4-flash-udq2kxl --suite veerman \
  --base-url http://127.0.0.1:1235/v1 --force > "$LOGDIR/udq2kxl-toolcall-veerman.log" 2>&1
say "veerman rc=$?"

say "humaneval START (expect ~3h)"
"$PY" scripts/bench2.py humaneval --examples 100 --model deepseek-v4-flash-udq2kxl \
  --max-tokens 32768 > "$LOGDIR/udq2kxl-humaneval.log" 2>&1
say "humaneval rc=$?"
say "cheap-signals DONE"
