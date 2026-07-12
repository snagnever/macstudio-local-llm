#!/usr/bin/env bash
# qwen3.6-35b-a3b-ud-mlx (unsloth UD-MLX-4bit) — Phase 2a: fast cheap signals.
# tool-calling (jdhodges 40 + veerman 12) → HumanEval (100) → MMLU (100), the
# quick legs of the committed ladder (LCB is the multi-hour tail, run separately
# only if these hold). Thinking ON, temp 0, seed 42, ctx 65k — matching how the
# @6bit anchors were produced (jdhodges 97.5 / veerman 75.0 / HumanEval 87 / MMLU 83).
#
# The model must be loaded with its ORIGINAL (thinking-on) chat template — quality
# benches run with reasoning enabled, unlike the no-think throughput sweep. The
# scenario driver restores the template on exit, so state is correct after Phase 1b.
#
# Usage: bash bench/qwen3.6-ud-mlx/scripts/run-ud-cheapsignals-fast.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
LMS=/Users/vitor/.lmstudio/bin/lms
PY=$REPO/.venv/bin/python
MODEL=qwen3.6-35b-a3b-ud-mlx
CTX=65536
LOGDIR=$REPO/bench/qwen3.6-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud-cheapsignals-fast-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

# Guard: template must be the ORIGINAL (thinking-on) variant for quality benches.
TMPL=/Users/vitor/.lmstudio/models/unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit/chat_template.jinja
if grep -q "BENCH no-think" "$TMPL"; then
  say "ABORT: template still patched no-think; restore chat_template.jinja.nothink-backup first"
  exit 1
fi

# CLEAN reload: `lms load` on an already-resident model is a no-op and keeps the
# in-memory template — after a no-think run that leaves thinking OFF. Unload first
# so LM Studio re-reads the (thinking-on) chat_template.jinja from disk.
say "clean reload (unload --all → load) so thinking-on template is re-read"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tail -1 | tee -a "$DRIVER"

# Assert thinking is ACTUALLY on (reasoning_tokens>0) before spending hours — the
# @6bit anchors are thinking-on, so a thinking-off run would be non-comparable.
say "verifying thinking is active"
RT=$(curl -s http://127.0.0.1:1234/v1/chat/completions -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 17*23? Think step by step.\"}],\"max_tokens\":200,\"temperature\":0}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("completion_tokens_details",{}).get("reasoning_tokens",0))')
say "reasoning_tokens on probe = $RT"
if [ "${RT:-0}" -lt 1 ]; then
  say "ABORT: thinking is OFF (reasoning_tokens=$RT). Template/in-memory state wrong — not running."
  exit 1
fi

cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }

say "1/4 tool-calling — jdhodges (40)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges 2>&1 | tee -a "$DRIVER"
say "jdhodges rc=${PIPESTATUS[0]}"

say "2/4 tool-calling — veerman (12)"
"$PY" scripts/tool_call_bench.py --model "$MODEL" --suite veerman 2>&1 | tee -a "$DRIVER"
say "veerman rc=${PIPESTATUS[0]}"

say "3/4 HumanEval (100)"
"$PY" scripts/bench2.py humaneval --model "$MODEL" --examples 100 2>&1 | tee -a "$DRIVER"
say "humaneval rc=${PIPESTATUS[0]}"

say "4/4 MMLU (100)"
"$PY" scripts/bench2.py mmlu --model "$MODEL" --examples 100 2>&1 | tee -a "$DRIVER"
say "mmlu rc=${PIPESTATUS[0]}"

say "Phase 2a fast cheap signals COMPLETE"
