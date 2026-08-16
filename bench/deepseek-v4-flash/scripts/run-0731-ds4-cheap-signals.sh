#!/usr/bin/env bash
# 0731 + ds4 Task 4 — jdhodges (40) -> Veerman (12) -> HumanEval (100), sequential.
#
# MODEL ID IS LOAD-BEARING: ds4-server defaults DeepSeek chat requests to
# high-effort thinking, and the only lever the harness exposes is the model id
# it puts in the request body. `deepseek-chat` is ds4's magic non-thinking id;
# any other id (including a descriptive one) silently turns thinking ON, which
# would break the A/B against the thinking-off baseline and, at these token
# caps, return empty content. So results land under the name `deepseek-chat`
# rather than a campaign name — see results/0731-ds4-campaign-log.md.
#
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-0731-ds4-cheap-signals.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
URL=http://127.0.0.1:8000/v1
MODEL=deepseek-chat
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/0731-ds4-cheap-signals-driver.log
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "cheap-signals START (0731 + ds4, thinking OFF via model id $MODEL)"

FREE_GB=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 150 ] || { say "ABORT: ${FREE_GB}GB free"; exit 1; }
# ds4-server has no /health; /v1/models is the liveness probe.
curl -sf --max-time 5 "$URL/models" >/dev/null || { say "ABORT: ds4-server down on :8000"; exit 1; }

# Assert thinking really is off before spending ~40 min: the non-thinking path
# answers "2+2" in a single token, the thinking path burns dozens.
NT=$(curl -s --max-time 120 "$URL/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 2+2? Answer with just the number.\"}],\"max_tokens\":256,\"temperature\":0}" \
  | "$ROOT/.venv/bin/python" -c "import json,sys; print(json.load(sys.stdin)['usage']['completion_tokens'])")
say "thinking-off check: completion_tokens=$NT (expect 1; >10 means thinking is ON)"
[ "$NT" -le 10 ] || { say "ABORT: thinking appears ON"; exit 1; }

PY=$ROOT/.venv/bin/python
cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=$URL
export BENCH_TIMEOUT=3600

say "jdhodges START (baseline 90.0%)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges \
  --base-url "$URL" --force > "$LOGDIR/0731-ds4-toolcall-jdhodges.log" 2>&1
say "jdhodges rc=$?"

say "veerman START (baseline 75.0%)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman \
  --base-url "$URL" --force > "$LOGDIR/0731-ds4-toolcall-veerman.log" 2>&1
say "veerman rc=$?"

say "humaneval START (baseline 95.0%; ~32 min expected at 33.6 t/s)"
"$PY" scripts/bench2.py humaneval --examples 100 --model "$MODEL" \
  --max-tokens 32768 > "$LOGDIR/0731-ds4-humaneval.log" 2>&1
say "humaneval rc=$?"
say "cheap-signals DONE"
