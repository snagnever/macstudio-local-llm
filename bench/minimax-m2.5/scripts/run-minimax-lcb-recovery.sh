#!/usr/bin/env bash
# LCB truncation-recovery: rerun the 5 questions that hit the 32k cap (Q8,19,38,44,48 —
# all hard) at max-tokens 57344, model at ctx 61440 (60k). Tests whether a bigger context
# recovers them. bench2 writes a SEPARATE summary (no auto-merge) — fold in manually after.
set -u
LOG=/tmp/minimax_lcb_recovery.log
exec > "$LOG" 2>&1
echo "=== LCB recovery start $(date -Iseconds) ==="

BREPO=/Users/vitor/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb
LMS=/Users/vitor/.lmstudio/bin/lms
export LMSTUDIO_URL=http://127.0.0.1:1234/v1
export BENCH_TIMEOUT=3600

echo "=== model state (expect ctx 61440, IDLE) ==="
"$LMS" ps | grep -iE "minimax|context" || true

cd "$BREPO" || { echo "ABORT: repo dir missing"; exit 1; }
echo "=== LCB Q8,19,38,44,48 @ max-tokens 57344, ctx 60k $(date -Iseconds) ==="
.venv/bin/python scripts/bench2.py livecodebench --examples 50 --only 8,19,38,44,48 \
  --model unsloth/minimax-m2.5 --lcb-version release_v6 --max-tokens 57344
RC=$?
echo "=== LCB recovery finished rc=$RC $(date -Iseconds) ==="
# leave model loaded (user's remote-tbench plan needs it resident)
echo "=== DONE (model left resident) $(date -Iseconds) ==="
