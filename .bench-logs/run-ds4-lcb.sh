#!/usr/bin/env bash
set -u
REPO=/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
cd "$REPO"
export LMSTUDIO_URL=http://127.0.0.1:1235/v1
export BENCH_TIMEOUT=3600
echo "=== LCB driver start $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py livecodebench --examples 50 \
  --model deepseek-v4-flash-iq2xs --lcb-version release_v6 --max-tokens 32768
echo "=== LCB driver end $(date -Iseconds) exit=$? ==="
