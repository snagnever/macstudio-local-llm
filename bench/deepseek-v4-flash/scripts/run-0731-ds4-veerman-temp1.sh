#!/usr/bin/env bash
# 0731 + ds4 Task 4b — Veerman at vendor-recommended sampling.
#
# The T4 run used temp 0 (deterministic A/B). The 0731 vendor card recommends
# temp 1.0 with top_p 0.95 for agentic scenarios. Veerman is the agentic suite
# and it stalled at 75% / veerman_hard 1/3 at temp 0 — exactly the axis 0731
# claims to improve. This re-runs it on-spec.
#
# Temp 1.0 is stochastic and Veerman is only 12 cases, so a single pass is
# noise. Run 3 seeds and read the distribution, not any one number.
#
# Requires the env-overridable sampling in tool_call_bench.py (BENCH_TEMPERATURE
# / BENCH_TOP_P / BENCH_SEED). Thinking still OFF via model id deepseek-chat.
#
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-0731-ds4-veerman-temp1.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
URL=http://127.0.0.1:8000/v1
MODEL=deepseek-chat
PY=$ROOT/.venv/bin/python
DRIVER=$LOGDIR/0731-ds4-veerman-temp1-driver.log
mkdir -p "$LOGDIR"
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "veerman temp1 START (temp=1.0 top_p=0.95, 3 seeds)"

curl -sf --max-time 5 "$URL/models" >/dev/null || { say "ABORT: ds4-server down"; exit 1; }

cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=$URL BENCH_TIMEOUT=3600
export BENCH_TEMPERATURE=1.0 BENCH_TOP_P=0.95

for S in 1 2 3; do
  export BENCH_SEED=$S
  say "seed=$S START"
  "$PY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman \
    --base-url "$URL" --force --run-prefix "toolcall_temp1_seed${S}" \
    > "$LOGDIR/0731-ds4-veerman-temp1-seed${S}.log" 2>&1
  say "seed=$S rc=$?"
done
say "veerman temp1 DONE"
