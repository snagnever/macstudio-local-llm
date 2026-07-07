#!/bin/bash
# Cheap coding+knowledge tail for agents-a1-xl-mlx (Qwen3.5-based thinking agentic fine-tune).
# HumanEval -> MMLU -> LiveCodeBench v6, all at --max-tokens 65536.
# Cheapest/safest first, spiral-prone LCB last. Detached-driver pattern (nohup/disown)
# because Bash-background silently kills long python runs past ~2h on this rig.
set -u
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb || exit 1

PY=/Users/vitor/LocalProjects/local-llms/.venv/bin/python
MODEL=agents-a1-xl-mlx
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
export BENCH_TIMEOUT=3600   # raised per-request timeout for slow thinking model at 65k cap

echo "===== CHEAP TAIL START $(date) model=$MODEL ====="

echo "----- [1/3] HumanEval n=100 $(date) -----"
$PY scripts/bench2.py humaneval --examples 100 --model "$MODEL" --max-tokens 65536
echo "----- HumanEval DONE rc=$? $(date) -----"

echo "----- [2/3] MMLU n=100 $(date) -----"
$PY scripts/bench2.py mmlu --examples 100 --model "$MODEL" --max-tokens 65536
echo "----- MMLU DONE rc=$? $(date) -----"

echo "----- [3/3] LiveCodeBench v6 n=50 $(date) -----"
$PY scripts/bench2.py livecodebench --examples 50 --model "$MODEL" --lcb-version release_v6 --max-tokens 65536
echo "----- LCB DONE rc=$? $(date) -----"

echo "===== CHEAP TAIL COMPLETE $(date) ====="
