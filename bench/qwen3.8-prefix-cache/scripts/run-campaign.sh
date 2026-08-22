#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CAMPAIGN="$ROOT/bench/qwen3.8-prefix-cache"
SCRIPTS="$CAMPAIGN/scripts"
RESULTS="$CAMPAIGN/results"
LOGS="$CAMPAIGN/logs"
STAGE="${1:-}"
DRY_RUN="${QWEN38_DRY_RUN:-0}"
REPEATS="${QWEN38_REPEATS:-3}"
INTER_RUN_SECONDS="${QWEN38_INTER_RUN_SECONDS:-45}"

MLX_RUNTIME_REVISION="${QWEN38_MLX_RUNTIME_REVISION:-v26.8.9}"
LLAMA_RUNTIME_REVISION="${QWEN38_LLAMA_RUNTIME_REVISION:-v0.2.0/b10566@bb4caa7540188872173c44d161602d9271386413}"
MLX_MODEL_REVISION="${QWEN38_MLX_MODEL_REVISION:-011e38296b3d2aa99245ed49a700459c4ac246b6}"
UNSLOTH_MODEL_REVISION="${QWEN38_UNSLOTH_MODEL_REVISION:-4ca720788d1e01f1bff70c033e0d0028fd02e502}"

ACTIVE_PID=""
MACMON_PID=""
MACMON_LOG=""

usage() {
  cat >&2 <<'EOF'
usage: run-campaign.sh {smoke|cache-32k|mtp-32k|omlx-smoke|omlx-cache-32k|omlx-mtp-32k|specprefill-16k|specprefill-32k|ane-16k|ane-32k|cache-65k|tool-loop|summary|native-262k}
EOF
}

cleanup() {
  if [[ -n "$ACTIVE_PID" ]] && kill -0 "$ACTIVE_PID" 2>/dev/null; then
    kill "$ACTIVE_PID" 2>/dev/null || true
    wait "$ACTIVE_PID" 2>/dev/null || true
  fi
  if [[ -n "$MACMON_PID" ]] && kill -0 "$MACMON_PID" 2>/dev/null; then
    kill "$MACMON_PID" 2>/dev/null || true
    wait "$MACMON_PID" 2>/dev/null || true
  fi
  ACTIVE_PID=""
  MACMON_PID=""
}
trap cleanup EXIT INT TERM

arm_metadata() {
  local arm="$1"
  case "$arm" in
    A|B|C)
      RUNTIME="mlx-serve"
      MODEL_ID="ddalcu/Qwen3.8-27B-MLX-Serve-8bit"
      RUNTIME_REVISION="$MLX_RUNTIME_REVISION"
      MODEL_REVISION="$MLX_MODEL_REVISION"
      PORT=11234
      LAUNCHER="$SCRIPTS/run-mlx-serve.sh"
      ;;
    D|E|F)
      RUNTIME="llama.cpp"
      MODEL_ID="unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL"
      RUNTIME_REVISION="$LLAMA_RUNTIME_REVISION"
      MODEL_REVISION="$UNSLOTH_MODEL_REVISION"
      PORT=8080
      LAUNCHER="$SCRIPTS/run-llama-cpp.sh"
      ;;
    G)
      RUNTIME="llama.cpp"
      MODEL_ID="unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL"
      RUNTIME_REVISION="$LLAMA_RUNTIME_REVISION"
      MODEL_REVISION="$UNSLOTH_MODEL_REVISION"
      PORT=8080
      LAUNCHER="$SCRIPTS/run-llama-cpp.sh"
      ;;
    H)
      RUNTIME="llama.cpp"
      MODEL_ID="unsloth/Qwen3.8-27B-GGUF:UD-Q8_K_XL"
      RUNTIME_REVISION="$LLAMA_RUNTIME_REVISION"
      MODEL_REVISION="$UNSLOTH_MODEL_REVISION"
      PORT=8080
      LAUNCHER="$SCRIPTS/run-llama-cpp.sh"
      ;;
    I)
      RUNTIME="oMLX"
      MODEL_ID="ddalcu/Qwen3.8-27B-MLX-Serve-8bit"
      RUNTIME_REVISION="v0.6.3rc2"
      MODEL_REVISION="$MLX_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-omlx.sh"
      ;;
    J|K|L|M|N|O)
      RUNTIME="oMLX"
      MODEL_ID="True2456/Qwen3.8-27B-AWQ-5.0bpw"
      RUNTIME_REVISION="v0.6.3rc2"
      MODEL_REVISION="dc699a76ddcbef44c188a8aee2ccc79ccc339a04"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-omlx.sh"
      ;;
    *)
      echo "unknown arm: $arm" >&2
      return 64
      ;;
  esac

  CACHE_ARGS=()
  MTP_ARGS=()
  SPECPREFILL_ARGS=()
  ANE_PREFILL_ARGS=()
  case "$arm" in
    B|C|E|F|G|H|K|L|M|N) CACHE_ARGS=(--cache-enabled) ;;
  esac
  case "$arm" in
    C|F|G|H) MTP_ARGS=(--mtp-enabled) ;;
    L|M|N) MTP_ARGS=(--mtp-enabled) ;;
  esac
  case "$arm" in
    M) SPECPREFILL_ARGS=(--specprefill=true --specprefill-keep-pct 0.40 --specprefill-threshold 8192) ;;
    N) SPECPREFILL_ARGS=(--specprefill=true --specprefill-keep-pct 0.50 --specprefill-threshold 8192) ;;
    J|K|L|O) SPECPREFILL_ARGS=(--specprefill=false) ;;
  esac
  case "$arm" in
    O) ANE_PREFILL_ARGS=(--ane-prefill-enabled) ;;
  esac
}

wait_for_server() {
  local base_url="$1"
  local attempts="${QWEN38_HEALTH_ATTEMPTS:-120}"
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl --silent --fail "$base_url/models" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "runtime did not become healthy at $base_url/models" >&2
  return 1
}

start_runtime() {
  local arm="$1"
  local context="$2"
  local log_file="$3"

  echo "+ QWEN38_CTX_SIZE=$context bash $LAUNCHER $arm"
  if command -v macmon >/dev/null; then
    MACMON_LOG="${log_file%.log}-macmon.jsonl"
    macmon pipe >"$MACMON_LOG" 2>&1 &
    MACMON_PID=$!
  fi
  QWEN38_CTX_SIZE="$context" bash "$LAUNCHER" "$arm" >"$log_file" 2>&1 &
  ACTIVE_PID=$!
}

finish_runtime() {
  local results_file="$1"
  local session_id="$2"
  cleanup
  python3 "$SCRIPTS/enrich_telemetry.py" \
    --results "$results_file" \
    --telemetry "$MACMON_LOG" \
    --session-id "$session_id"
  if [[ "$INTER_RUN_SECONDS" != "0" ]]; then
    sleep "$INTER_RUN_SECONDS"
  fi
}

validate_mtp_log() {
  local arm="$1"
  local log_file="$2"
  case "$arm" in
    C|F|G|H)
      if ! grep -Eiq 'mtp|draft' "$log_file"; then
        echo "arm $arm did not report MTP/draft activation in $log_file" >&2
        return 1
      fi
      ;;
  esac
}

wait_for_cooldown() {
  echo "GPU cooldown gate: below 50C"
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  local attempt sample temperature
  for ((attempt = 1; attempt <= 120; attempt++)); do
    sample="$(macmon pipe --samples 1 2>/dev/null)"
    temperature="$(jq -er '.temp.gpu_temp_avg' <<<"$sample")"
    if awk "BEGIN { exit !($temperature < 50.0) }"; then
      echo "GPU temperature ready: ${temperature}C"
      return 0
    fi
    sleep 5
  done
  echo "GPU did not cool below 50C" >&2
  return 1
}

run_cache_arm() {
  local arm="$1"
  local context="$2"
  arm_metadata "$arm"
  echo "RUN arm=$arm context=$context mode=cache"
  wait_for_cooldown
  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ "$RUNTIME" == "oMLX" ]]; then
      echo "+ QWEN38_CTX_SIZE=$context bash $LAUNCHER $arm"
    else
      bash "$LAUNCHER" "$arm" --print
    fi
    return 0
  fi

  mkdir -p "$RESULTS" "$LOGS"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local runtime_log="$LOGS/${stamp}-${arm}-${context}-runtime.log"
  local session_id="${stamp}-${arm}-${context}-cache"
  start_runtime "$arm" "$context" "$runtime_log"
  wait_for_server "http://127.0.0.1:${PORT}/v1"

  PROBE_COMMAND=(
    python3 "$SCRIPTS/cache_probe.py"
    --base-url "http://127.0.0.1:${PORT}/v1"
    --model "$MODEL_ID"
    --runtime "$RUNTIME"
    --runtime-revision "$RUNTIME_REVISION"
    --model-revision "$MODEL_REVISION"
    --arm "$arm"
    --session-id "$session_id"
    --context "$context"
    --repeat "$REPEATS"
    --output "$RESULTS/cache-probe.jsonl"
    --metrics-url "http://127.0.0.1:${PORT}/metrics"
  )
  if [[ "${#CACHE_ARGS[@]}" -gt 0 ]]; then
    PROBE_COMMAND+=("${CACHE_ARGS[@]}")
  fi
  if [[ "${#MTP_ARGS[@]}" -gt 0 ]]; then
    PROBE_COMMAND+=("${MTP_ARGS[@]}")
  fi
  if [[ "${#SPECPREFILL_ARGS[@]}" -gt 0 ]]; then
    PROBE_COMMAND+=("${SPECPREFILL_ARGS[@]}")
  fi
  if [[ "${#ANE_PREFILL_ARGS[@]}" -gt 0 ]]; then
    PROBE_COMMAND+=("${ANE_PREFILL_ARGS[@]}")
  fi
  printf '+ %q ' "${PROBE_COMMAND[@]}"
  printf '\n'
  "${PROBE_COMMAND[@]}"

  validate_mtp_log "$arm" "$runtime_log"
  finish_runtime "$RESULTS/cache-probe.jsonl" "$session_id"
}

run_tool_arm() {
  local arm="$1"
  arm_metadata "$arm"
  echo "RUN arm=$arm context=65536 mode=tool-loop"
  wait_for_cooldown
  if [[ "$DRY_RUN" == "1" ]]; then
    bash "$LAUNCHER" "$arm" --print
    return 0
  fi

  mkdir -p "$RESULTS" "$LOGS"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local runtime_log="$LOGS/${stamp}-${arm}-tool-loop-runtime.log"
  local session_id="${stamp}-${arm}-tool-loop"
  start_runtime "$arm" 65536 "$runtime_log"
  wait_for_server "http://127.0.0.1:${PORT}/v1"

  TOOL_COMMAND=(
    python3 "$SCRIPTS/tool_loop.py"
    --base-url "http://127.0.0.1:${PORT}/v1"
    --model "$MODEL_ID"
    --runtime "$RUNTIME"
    --runtime-revision "$RUNTIME_REVISION"
    --model-revision "$MODEL_REVISION"
    --arm "$arm"
    --session-id "$session_id"
    --output "$RESULTS/tool-loop.jsonl"
    --metrics-url "http://127.0.0.1:${PORT}/metrics"
  )
  if [[ "${#CACHE_ARGS[@]}" -gt 0 ]]; then
    TOOL_COMMAND+=("${CACHE_ARGS[@]}")
  fi
  if [[ "${#MTP_ARGS[@]}" -gt 0 ]]; then
    TOOL_COMMAND+=("${MTP_ARGS[@]}")
  fi
  printf '+ %q ' "${TOOL_COMMAND[@]}"
  printf '\n'
  "${TOOL_COMMAND[@]}"

  validate_mtp_log "$arm" "$runtime_log"
  finish_runtime "$RESULTS/tool-loop.jsonl" "$session_id"
}

summarize() {
  echo "+ python3 $SCRIPTS/summarize.py"
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  python3 "$SCRIPTS/summarize.py"
}

survivor_arms() {
  if [[ ! -f "$RESULTS/runtime-survivors.json" ]]; then
    summarize >/dev/null
  fi
  jq -r '.survivors[] | select(.passed == true) | .arm' \
    "$RESULTS/runtime-survivors.json"
}

run_arms() {
  local context="$1"
  shift
  local arm
  for arm in "$@"; do
    run_cache_arm "$arm" "$context"
  done
}

case "$STAGE" in
  smoke)
    run_arms 8192 A B D E
    ;;
  cache-32k)
    run_arms 32768 B E
    ;;
  mtp-32k)
    run_arms 32768 C F G H
    ;;
  omlx-smoke)
    run_arms 8192 I J
    ;;
  omlx-cache-32k)
    run_arms 32768 K
    ;;
  omlx-mtp-32k)
    run_arms 32768 L
    ;;
  specprefill-16k)
    run_arms 16384 L M N
    ;;
  specprefill-32k)
    run_arms 32768 L M N
    ;;
  ane-16k)
    run_arms 16384 J O
    ;;
  ane-32k)
    run_arms 32768 J O
    ;;
  cache-65k)
    if [[ "$DRY_RUN" == "1" ]]; then
      run_arms 65536 C E F G H
    else
      summarize || true
      ARMS=()
      while IFS= read -r ARM; do
        [[ -n "$ARM" ]] && ARMS+=("$ARM")
      done < <(survivor_arms)
      if [[ "${#ARMS[@]}" -eq 0 ]]; then
        echo "no passing production arms are available for 65K" >&2
        exit 2
      fi
      run_arms 65536 "${ARMS[@]}"
    fi
    ;;
  tool-loop)
    if [[ "$DRY_RUN" == "1" ]]; then
      for ARM in C E F G H; do run_tool_arm "$ARM"; done
    else
      summarize || true
      ARMS=()
      while IFS= read -r ARM; do
        [[ -n "$ARM" ]] && ARMS+=("$ARM")
      done < <(survivor_arms)
      if [[ "${#ARMS[@]}" -eq 0 ]]; then
        echo "no passing production arms are available for the tool loop" >&2
        exit 2
      fi
      for ARM in "${ARMS[@]}"; do run_tool_arm "$ARM"; done
    fi
    ;;
  summary)
    summarize
    ;;
  native-262k)
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "RUN winner context=262144 mode=native-smoke"
      exit 0
    fi
    SELECTION="$RESULTS/selection.json"
    if [[ ! -f "$SELECTION" ]]; then
      echo "selection is missing: $SELECTION" >&2
      exit 2
    fi
    WINNER_ARM="$(jq -er '.winner.arm' "$SELECTION")"
    QWEN38_REPEATS=1 run_cache_arm "$WINNER_ARM" 262144
    ;;
  *)
    usage
    exit 64
    ;;
esac
