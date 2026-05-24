#!/usr/bin/env bash
set -euo pipefail
source /Users/vitor/LocalProjects/local-llms/.venv/bin/activate
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
export LMSTUDIO_URL="http://127.0.0.1:1234/v1"
MODEL="gemma-4-26b-a4b-it-mlx@4bit"
LOG=/Users/vitor/LocalProjects/local-llms/.bench-logs/gemma-4bit-knowledge.log

echo "=== MATH n=100 (resume from scratch) ===" | tee -a "$LOG"
python3 scripts/bench2.py math --examples 100 --model "$MODEL" 2>&1 | tee -a "$LOG"

echo "=== DROP n=100 ===" | tee -a "$LOG"
python3 scripts/bench2.py drop --examples 100 --model "$MODEL" 2>&1 | tee -a "$LOG"

echo "=== GPQA n=100 --max-tokens 65536 ===" | tee -a "$LOG"
python3 scripts/bench2.py gpqa --examples 100 --model "$MODEL" --max-tokens 65536 2>&1 | tee -a "$LOG"

echo "=== DONE @4bit knowledge sweep (resumed) ===" | tee -a "$LOG"
