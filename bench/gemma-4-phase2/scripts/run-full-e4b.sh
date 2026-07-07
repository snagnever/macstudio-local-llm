#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source $REPO/.venv/bin/activate
export LMSTUDIO_URL="http://127.0.0.1:1234/v1"

MODEL="gemma-4-e4b-it-mlx"
LABEL="gemma-4-e4b-mlx-8bit"
LOG=$REPO/bench/gemma-4-phase2/logs/gemma-e4b-full.log
M4=$REPO/tools/local-llm-bench-m4-32gb
BENCH=$REPO/tools/local-llm-bench

echo "=== Step 1: throughput sweep ($LABEL) ===" | tee -a "$LOG"
cd "$BENCH" && python3 bench.py --backend lmstudio --base-url http://127.0.0.1:1234 --model "$MODEL" --model-label "$LABEL" 2>&1 | tee -a "$LOG"

echo "=== Step 2: tool-call jdhodges ===" | tee -a "$LOG"
cd "$M4" && python3 scripts/tool_call_bench.py --model "$MODEL" --suite jdhodges --base-url http://127.0.0.1:1234/v1 2>&1 | tee -a "$LOG"

echo "=== Step 2: tool-call veerman ===" | tee -a "$LOG"
python3 scripts/tool_call_bench.py --model "$MODEL" --suite veerman --base-url http://127.0.0.1:1234/v1 2>&1 | tee -a "$LOG"

echo "=== Step 3: HumanEval n=100 ===" | tee -a "$LOG"
python3 scripts/bench2.py humaneval --examples 100 --model "$MODEL" 2>&1 | tee -a "$LOG"

echo "=== Step 4: LiveCodeBench n=50 release_v6 ===" | tee -a "$LOG"
python3 scripts/bench2.py livecodebench --examples 50 --model "$MODEL" --lcb-version release_v6 2>&1 | tee -a "$LOG"

echo "=== Step 5: MMLU n=100 ===" | tee -a "$LOG"
python3 scripts/bench2.py mmlu --examples 100 --model "$MODEL" 2>&1 | tee -a "$LOG"

echo "=== Step 6: MATH n=100 ===" | tee -a "$LOG"
python3 scripts/bench2.py math --examples 100 --model "$MODEL" 2>&1 | tee -a "$LOG"

echo "=== Step 7: DROP n=100 ===" | tee -a "$LOG"
python3 scripts/bench2.py drop --examples 100 --model "$MODEL" 2>&1 | tee -a "$LOG"

echo "=== Step 8: GPQA n=100 --max-tokens 65536 ===" | tee -a "$LOG"
python3 scripts/bench2.py gpqa --examples 100 --model "$MODEL" --max-tokens 65536 2>&1 | tee -a "$LOG"

echo "=== DONE $LABEL full suite ===" | tee -a "$LOG"
