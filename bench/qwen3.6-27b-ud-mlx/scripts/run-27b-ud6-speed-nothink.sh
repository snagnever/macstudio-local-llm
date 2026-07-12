#!/usr/bin/env bash
# qwen3.6-27b-ud-mlx@6bit (unsloth UD-MLX-6bit, dense 27B) — speed, THINKING OFF.
# Corrects the earlier thinking-on speed run: the daily-driver anchors
# (~20 t/s scenario gen_tps, doc-summary 88/150 tokens) were themselves produced
# thinking-OFF — tight per-turn max_tokens caps (150) leave no room for a
# reasoning pass. Comparing thinking-on numbers against a thinking-off anchor
# was apples-to-oranges. This script forces no-think via the same chat-template
# patch used on the 35B-A3B UD-4bit campaign (enable_thinking conditional
# replaced with an unconditional pre-closed <think></think> block), runs
# speed_probe.py + the 4-scenario sweep, then restores the template on exit.
#
# Usage: bash bench/qwen3.6-27b-ud-mlx/scripts/run-27b-ud6-speed-nothink.sh
set -u

REPO=/Users/vitor/LocalProjects/local-llms
BENCH=$REPO/tools/local-llm-bench-m4-32gb
HARNESS=$REPO/tools/local-llm-bench
LMS=/Users/vitor/.lmstudio/bin/lms
PY=$REPO/.venv/bin/python
PY3=python3
MODEL="qwen3.6-27b-ud-mlx@6bit"
LABEL=qwen3.6-27b-ud-mlx-6bit-nothink
CTX=65536
TMPL=/Users/vitor/.lmstudio/models/unsloth/Qwen3.6-27B-UD-MLX-6bit/chat_template.jinja
LOGDIR=$REPO/bench/qwen3.6-27b-ud-mlx/logs
mkdir -p "$LOGDIR"
DRIVER=$LOGDIR/ud6-speed-nothink-driver.log
: > "$DRIVER"
say(){ echo "=== $* $(date -Iseconds) ===" | tee -a "$DRIVER"; }

restore_template(){
  if [ -f "$TMPL.nothink-backup" ]; then
    cp "$TMPL.nothink-backup" "$TMPL" && say "template RESTORED from backup"
    "$LMS" unload --all 2>/dev/null
    "$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tail -2 | tee -a "$DRIVER"
    say "model reloaded thinking-on (post-restore) for Phase 2 continuity"
  else
    say "WARN: no template backup to restore"
  fi
}
trap restore_template EXIT

if ! grep -q "BENCH no-think" "$TMPL"; then
  say "ABORT: template is not the patched no-think variant (expected 'BENCH no-think' marker)"
  exit 1
fi

say "27B UD-6bit no-think speed START — reloading so LM Studio reads patched template"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 1 --ttl 172800 -y 2>&1 | tail -2 | tee -a "$DRIVER"
"$LMS" ps 2>&1 | tee -a "$DRIVER"

RT=$(curl -s http://127.0.0.1:1234/v1/chat/completions -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"What is 17*23? Think step by step.\"}],\"max_tokens\":200,\"temperature\":0}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["usage"].get("completion_tokens_details",{}).get("reasoning_tokens",0))')
say "reasoning_tokens on probe = $RT (expect 0)"
if [ "${RT:-0}" -gt 0 ]; then
  say "ABORT: thinking still ON (reasoning_tokens=$RT) — template patch not effective"
  exit 1
fi

export LMSTUDIO_URL=http://127.0.0.1:1234/v1
cd "$BENCH" || { say "ABORT: bench dir missing"; exit 1; }
say "running speed_probe.py (parallel 1, no-think)"
"$PY" scripts/speed_probe.py "$MODEL" results/speed_probe 2>&1 | tee -a "$DRIVER"
say "speed probe rc=${PIPESTATUS[0]}"

say "reloading at --parallel 4 for scenario sweep"
"$LMS" unload --all 2>/dev/null
"$LMS" load "$MODEL" --context-length $CTX --gpu max --parallel 4 --ttl 172800 -y 2>&1 | tail -2 | tee -a "$DRIVER"

cd "$HARNESS" || { say "ABORT: harness dir missing"; exit 1; }
for sc in creative-writing doc-summary ops-agent prefill-test; do
  say "scenario: $sc"
  "$PY3" bench.py \
    --backend lmstudio \
    --scenario "scenarios/$sc.json" \
    --model "$MODEL" \
    --model-label "$LABEL" 2>&1 | tee -a "$DRIVER"
  say "scenario $sc rc=${PIPESTATUS[0]}"
done

say "27B UD-6bit no-think speed COMPLETE — results under tools/local-llm-bench/results/$LABEL/"
# EXIT trap restores the original (thinking-on) template + reloads
