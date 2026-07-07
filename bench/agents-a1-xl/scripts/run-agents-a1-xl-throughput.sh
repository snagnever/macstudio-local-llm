#!/bin/bash
# Effective-throughput scenarios for agents-a1-xl-mlx (text-only, 4 scenarios).
# Default thinking mode (as the model naturally runs) — consistent with its other benches.
set -u
cd /Users/vitor/LocalProjects/local-llms/tools/local-llm-bench || exit 1

MODEL=agents-a1-xl-mlx
LABEL=agents-a1-xl-mlx
URL=http://127.0.0.1:1234   # NOTE: bench.py appends /v1/chat/completions itself — do NOT add /v1 (that's a bench2.py convention). A double /v1 hits an endpoint that drops reasoning_content.

echo "===== THROUGHPUT START $(date) model=$MODEL ====="
for sc in ops-agent doc-summary prefill-test creative-writing; do
  echo "----- scenario: $sc $(date) -----"
  python3 bench.py --backend lmstudio --base-url "$URL" \
    --model "$MODEL" --model-label "$LABEL" \
    --scenario "scenarios/${sc}.json"
  echo "----- $sc DONE rc=$? $(date) -----"
done
echo "===== THROUGHPUT COMPLETE $(date) ====="
