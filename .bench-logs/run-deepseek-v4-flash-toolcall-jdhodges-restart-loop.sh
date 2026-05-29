#!/usr/bin/env bash
# Phase 3 #10 — DeepSeek V4 Flash tool-call jdhodges, restart-per-batch.
#
# Runs the jdhodges suite in 5 batches of 8 cases each. Between batches,
# kills + restarts mlx_lm.server cold to clear any Metal device wedge from
# accumulated cached state. ~5 min server warm-load per batch + ~5-15 min
# per batch of 8 = ~60-90 min total.
#
# Pattern: nohup ... & disown (this rig lacks setsid; PPID=1 survives
# Claude harness wall-clock kills).
#
# Usage:
#   nohup bash .bench-logs/run-deepseek-v4-flash-toolcall-jdhodges-restart-loop.sh > /dev/null 2>&1 & disown
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_PATH="/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ"
VENV_PY="$REPO/venvs/mlx-v4-flash/bin/python"
BENCH_PY="$REPO/.venv/bin/python"

LOGDIR="$REPO/.bench-logs"
DRIVER_LOG="$LOGDIR/jdhodges-restart-loop-driver.log"
BENCH_LOG="$LOGDIR/jdhodges-restart-loop-bench.log"
SERVER_LOG="$LOGDIR/jdhodges-restart-loop-server.log"

declare -a BATCHES=(
  "sel_weather_portland,sel_currency_usd_eur,sel_timezone_tokyo,sel_web_python_release,sel_reminder_dentist,sel_email_quick,sel_calendar_create,sel_calendar_read_week"
  "arg_weather_units_celsius,arg_currency_jpy,arg_email_with_cc,arg_event_with_attendees,arg_timezone_london,arg_reminder_iso_time,arg_calendar_range_month,arg_search_verbatim"
  "multi_weather_parallel,multi_usd_eur_sequential,multi_paris_celsius_fahrenheit,multi_email_after_calendar_read,multi_weather_two_cities_holdout,multi_convert_two_currencies,multi_search_then_remind,multi_time_and_weather"
  "edge_photosynthesis,edge_joke,edge_math_simple,edge_feeling_down,edge_vague_reminder,edge_vague_email,edge_define_word,edge_language_greeting"
  "fmt_email_no_cc,fmt_email_three_cc,fmt_event_four_attendees,fmt_weather_fahrenheit_enum,fmt_weather_no_units,fmt_currency_decimal_amount,fmt_event_no_attendees,fmt_calendar_read_single_day"
)
BATCH_NAMES=("sel" "arg" "multi" "edge" "fmt")

log() {
  echo "[$(date +%H:%M:%S)] $*" >> "$DRIVER_LOG"
}

restart_server() {
  log "Killing existing mlx_lm.server (if any)..."
  pkill -f mlx_lm.server 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    sleep 2
    pgrep -f mlx_lm.server >/dev/null || break
  done
  log "Launching mlx_lm.server (patched, chunk=2 + clear_cache)..."
  nohup "$VENV_PY" -m mlx_lm.server \
    --model "$MODEL_PATH" \
    --chat-template-args '{"enable_thinking":false}' \
    --host 0.0.0.0 --port 8765 \
    --max-tokens 65536 --temp 0.0 \
    >> "$SERVER_LOG" 2>&1 &
  disown
  log "Warming up (96 GB load, up to 6 min)..."
  for attempt in 1 2 3; do
    sleep 5
    if curl -sS -m 360 http://127.0.0.1:8765/v1/chat/completions \
        -H 'Content-Type: application/json' \
        -d "{\"model\":\"$MODEL_PATH\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":4}" \
        > /dev/null 2>&1; then
      log "Server ready (warmup attempt $attempt)"
      return 0
    fi
    log "Warmup attempt $attempt failed; retrying..."
  done
  log "ERROR: server failed to warm up after 3 attempts"
  return 1
}

run_batch() {
  local batch_idx=$1
  local batch_name=$2
  local case_ids=$3
  log "=== Batch ${batch_idx} (${batch_name}, 8 cases) ==="
  cd "$REPO/tools/local-llm-bench-m4-32gb"
  "$BENCH_PY" scripts/tool_call_bench.py \
    --model "$MODEL_PATH" \
    --suite jdhodges \
    --base-url http://127.0.0.1:8765/v1 \
    --only "$case_ids" \
    --force \
    --run-prefix "toolcall_${batch_name}" \
    >> "$BENCH_LOG" 2>&1
  local rc=$?
  log "Batch ${batch_idx} rc=$rc"
}

log "=== Driver start $(date -Iseconds) ==="

for i in 0 1 2 3 4; do
  if ! restart_server; then
    log "Skipping batch $((i+1)) due to server restart failure"
    continue
  fi
  run_batch $((i+1)) "${BATCH_NAMES[$i]}" "${BATCHES[$i]}"
done

log "Killing final server..."
pkill -f mlx_lm.server 2>/dev/null || true
log "=== Driver done $(date -Iseconds) ==="
