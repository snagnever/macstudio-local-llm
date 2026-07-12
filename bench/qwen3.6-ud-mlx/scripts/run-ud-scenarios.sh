#!/usr/bin/env bash
# qwen3.6-35b-a3b-ud-mlx (unsloth UD-MLX-4bit) — scenario throughput sweep.
# Phase 1b of bench/qwen3.6-ud-mlx/plan.md. tools/local-llm-bench harness, 4 text
# scenarios, gen + effective t/s, vs the @6bit no-think anchors (91.6/91.7/85.5/85.5 gen).
#
# NO-THINK MECHANISM (why not --no-think): the harness's --no-think patches the
# external chat_template.jinja by string-replacing the *Qwen3.5* add_generation_prompt
# block. This is a *Qwen3.6* template with an `enable_thinking` conditional the
# replace doesn't match, so --no-think would silently no-op and leave thinking ON
# (low-cap scenarios then error). Instead we patch the template directly to force
# the pre-closed <think></think> block (done out-of-band, backup at
# chat_template.jinja.nothink-backup), RELOAD so LM Studio picks it up, run with the
# plain served id (passes check_backend + routes the API), then RESTORE the backup.
#
# Usage: bash bench/qwen3.6-ud-mlx/scripts/run-ud-scenarios.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
HARNESS=$REPO/tools/local-llm-bench
LMS=/Users/vitor/.lmstudio/bin/lms
PY=python3
MODEL=qwen3.6-35b-a3b-ud-mlx                 # served id: passes check_backend + routes API
LABEL=qwen3.6-35b-a3b-ud-mlx-4bit
CTX=65536
TMPL=/Users/vitor/.lmstudio/models/unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit/chat_template.jinja
LOGDIR=$REPO/bench/qwen3.6-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud-scenarios-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

restore_template(){
  if [ -f "$TMPL.nothink-backup" ]; then
    cp "$TMPL.nothink-backup" "$TMPL" && say "template RESTORED from backup"
  else
    say "WARN: no template backup to restore"
  fi
}
trap restore_template EXIT

# Sanity: template must already be the patched (no-think) variant before we start.
if ! grep -q "BENCH no-think" "$TMPL"; then
  say "ABORT: template is not the patched no-think variant (expected 'BENCH no-think' marker)"
  exit 1
fi

say "ud-mlx scenario sweep START — reloading so LM Studio reads the patched (no-think) template"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

cd "$HARNESS" || { say "ABORT: harness dir missing"; exit 1; }
for sc in creative-writing doc-summary ops-agent prefill-test; do
  say "scenario: $sc"
  "$PY" bench.py \
    --backend lmstudio \
    --scenario "scenarios/$sc.json" \
    --model "$MODEL" \
    --model-label "$LABEL" 2>&1 | tee -a "$DRIVER"
  say "scenario $sc rc=${PIPESTATUS[0]}"
done

say "ud-mlx scenario sweep COMPLETE — results under tools/local-llm-bench/results/$LABEL/"
# EXIT trap restores the original template
