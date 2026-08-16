#!/usr/bin/env bash
# 0731 + ds4 Task 4-think — the with-thinking half of the cheap-signals A/B.
#
# T4 measured jdhodges / Veerman / HumanEval with thinking OFF. This repeats
# them with thinking HIGH (ds4's default for model id deepseek-v4-flash) to see
# whether reasoning moves the two soft spots: HumanEval (-5 vs baseline) and the
# stuck agentic axis. The vendor's own headline numbers (MMLU-Pro 86, LCB 91.6)
# are all thinking-mode, so this is the apples-to-apples-with-the-card read.
#
# Two knobs matter under thinking:
#   * model id deepseek-v4-flash (NOT deepseek-chat) turns thinking ON.
#   * max_tokens must be generous — the model spends hundreds of tokens
#     reasoning before the visible answer/tool call; at the stock 4096 a tool
#     call can be truncated away and score a false 0 (seen at 2048 in T1).
# reasoning_effort stays at ds4's default High; Max needs --ctx >= 393216, which
# this 256k server cannot provide, so Max is out of scope here.
#
# Usage: nohup bash bench/deepseek-v4-flash/scripts/run-0731-ds4-think.sh >/dev/null 2>&1 & disown
set -u
ROOT=/Users/vitor/LocalProjects/local-llms
LOGDIR=$ROOT/bench/deepseek-v4-flash/logs
URL=http://127.0.0.1:8000/v1
MODEL=deepseek-v4-flash      # thinking ON
PY=$ROOT/.venv/bin/python
DRIVER=$LOGDIR/0731-ds4-think-driver.log
mkdir -p "$LOGDIR"
say(){ echo "=== $* $(date -Iseconds) ===" >> "$DRIVER"; }
say "think START (model=$MODEL, reasoning_effort=High default)"

curl -sf --max-time 5 "$URL/models" >/dev/null || { say "ABORT: ds4-server down"; exit 1; }

# Preflight: confirm thinking is actually ON (a plain 2+2 should burn >10 tokens
# in thinking mode vs 1 token thinking-off), and that a longer generation still
# returns non-empty visible content within the raised budget (guards against the
# T1 "0 chars at 2048" failure before spending ~1h).
NT=$(curl -s --max-time 300 "$URL/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 2+2? Answer with just the number.\"}],\"max_tokens\":16384,\"temperature\":0}" \
  | "$PY" -c "import json,sys;d=json.load(sys.stdin);u=d['usage'];print(u['completion_tokens'],len((d['choices'][0]['message'].get('content') or '').strip()))")
CT=${NT% *}; CHARS=${NT#* }
say "preflight: completion_tokens=$CT visible_chars=$CHARS (expect tokens>10 AND chars>0)"
[ "$CT" -gt 10 ] || { say "ABORT: thinking not ON (got $CT tokens)"; exit 1; }
[ "$CHARS" -gt 0 ] || { say "ABORT: 0 visible chars — model never finished reasoning at 16384"; exit 1; }

cd "$ROOT/tools/local-llm-bench-m4-32gb"
export LMSTUDIO_URL=$URL BENCH_TIMEOUT=7200
export TOOLBENCH_MAX_TOKENS=16384        # room for reasoning + the tool call

say "jdhodges START (thinking-off was 97.5%)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges \
  --base-url "$URL" --force --run-prefix toolcall_think \
  > "$LOGDIR/0731-ds4-think-jdhodges.log" 2>&1
say "jdhodges rc=$?"

say "veerman START (thinking-off was 75.0%)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman \
  --base-url "$URL" --force --run-prefix toolcall_think \
  > "$LOGDIR/0731-ds4-think-veerman.log" 2>&1
say "veerman rc=$?"

say "humaneval START (thinking-off was 90.0%; slower — reasoning tax)"
# bench2.py has no --run-prefix; the model id (deepseek-v4-flash) already keeps
# these files distinct from the thinking-off deepseek-chat runs.
"$PY" scripts/bench2.py humaneval --examples 100 --model "$MODEL" \
  --max-tokens 32768 \
  > "$LOGDIR/0731-ds4-think-humaneval.log" 2>&1
say "humaneval rc=$?"
say "think DONE"
