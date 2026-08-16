#!/usr/bin/env bash
# 0731 + ds4 Task 5 — LiveCodeBench v6 (50), thinking HIGH.
#
# Two questions this run answers:
#   1. Does thinking pay on the one hard-code suite? (T4-think showed it does not
#      pay on tool-calling or standard HumanEval; LCB is where it might.)
#   2. Does ds4's KV manager avoid the llama.cpp KV-eviction bug? The baseline
#      (UD-Q2_K_XL on llama-server, -np 1) lost 12/50 to HTTP-500: a spiraled
#      case filled the single slot's KV to the -c ceiling and the next case's
#      prefill found no free cells. ds4 manages KV itself — if the empties
#      vanish, the raw score becomes trustworthy for the first time.
#
# Long job. Baseline (thinking OFF) took 10.5h; thinking ON is slower — the
# reasoning also competes with code for the 32k budget, so expect truncations.
# Overnight.
#
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-0731-ds4-lcb-think.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
URL=http://127.0.0.1:8000/v1
MODEL=deepseek-v4-flash      # thinking ON (High)
PY=$ROOT/.venv/bin/python
DRIVER=$LOGDIR/0731-ds4-lcb-think-driver.log
mkdir -p "$LOGDIR"
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "LCB-think START (model=$MODEL, LCB v6 x50, max_tokens 32768)"

FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: ${FREE_GB}GB free"; exit 1; }
curl -sf --max-time 5 "$URL/models" >/dev/null || { say "ABORT: ds4-server down"; exit 1; }

# Confirm thinking is ON before an overnight commitment.
CT=$(curl -s --max-time 300 "$URL/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 2+2? Answer with just the number.\"}],\"max_tokens\":16384,\"temperature\":0}" \
  | "$PY" -c "import json,sys;print(json.load(sys.stdin)['usage']['completion_tokens'])")
say "thinking-on check: completion_tokens=$CT (expect >10)"
[ "$CT" -gt 10 ] || { say "ABORT: thinking not ON"; exit 1; }

cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=$URL BENCH_TIMEOUT=3600
"$PY" scripts/bench2.py livecodebench --examples 50 \
  --model "$MODEL" --lcb-version release_v6 --max-tokens 32768 \
  > "$LOGDIR/0731-ds4-lcb-think.log" 2>&1
RC=$?
say "LCB rc=$RC"

# KV-eviction check: count HTTP-500 / error finishes in the raw jsonl.
JSONL=$(ls -t benchmarks/runs/livecodebench_deepseek-v4-flash_*.jsonl 2>/dev/null | head -1)
if [ -n "$JSONL" ]; then
  ERRS=$("$PY" -c "
import json,sys
n=err=0
for line in open('$JSONL'):
    try: d=json.loads(line)
    except: continue
    n+=1
    if d.get('finish_reason') in ('error',) or 'HTTP Error 500' in str(d.get('error','')): err+=1
print(f'{err} error/500 of {n}')
")
  say "KV-eviction check: $ERRS (baseline had 12/50)"
fi
say "LCB-think DONE"
