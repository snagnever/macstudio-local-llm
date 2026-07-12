#!/usr/bin/env bash
# qwen3.6-27b-ud-mlx@6bit (unsloth UD-MLX-6bit, dense 27B) — Phase 2: cheap signals.
# tool-calling (jdhodges 40 + veerman 12) -> HumanEval (100) -> MMLU (100), the
# gate for a daily-driver replacement. Thinking ON, temp 0, seed 42, ctx 65k —
# matching how the @6bit anchors were produced
# (jdhodges 97.5 / veerman 75.0 / HumanEval 87 / MMLU 83).
#
# Usage: bash bench/qwen3.6-27b-ud-mlx/scripts/run-27b-ud6-cheapsignals.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
LMS=/Users/vitor/.lmstudio/bin/lms
PY=$REPO/.venv/bin/python
MODEL="qwen3.6-27b-ud-mlx@6bit"
CTX=65536
LOGDIR=$REPO/bench/qwen3.6-27b-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud6-cheapsignals-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

# CLEAN reload so LM Studio re-reads the (thinking-on) chat_template from disk.
say "clean reload (unload --all -> load) thinking-on"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tail -1 | tee -a "$DRIVER"

# Assert thinking is ON (reasoning_tokens>0) — @6bit anchors are thinking-on.
say "verifying thinking is active"
RT=$(curl -s http://127.0.0.1:1234/v1/chat/completions -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 17*23? Think step by step.\"}],\"max_tokens\":200,\"temperature\":0}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("completion_tokens_details",{}).get("reasoning_tokens",0))')
say "reasoning_tokens on probe = $RT"
if [ "${RT:-0}" -lt 1 ]; then
  say "ABORT: thinking is OFF (reasoning_tokens=$RT). Not running."
  exit 1
fi

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }

say "1/4 tool-calling — jdhodges (40)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges --force 2>&1 | tee -a "$DRIVER"
say "jdhodges rc=${PIPESTATUS[0]}"

say "2/4 tool-calling — veerman (12)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman --force 2>&1 | tee -a "$DRIVER"
say "veerman rc=${PIPESTATUS[0]}"

say "3/4 HumanEval (100)"
"$PY" scripts/bench2.py humaneval --model "$MODEL" --examples 100 2>&1 | tee -a "$DRIVER"
say "humaneval rc=${PIPESTATUS[0]}"

say "4/4 MMLU (100)"
"$PY" scripts/bench2.py mmlu --model "$MODEL" --examples 100 2>&1 | tee -a "$DRIVER"
say "mmlu rc=${PIPESTATUS[0]}"

say "Phase 2 cheap signals COMPLETE"
