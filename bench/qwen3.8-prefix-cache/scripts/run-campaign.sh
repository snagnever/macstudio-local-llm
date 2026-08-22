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
SPECPREFILL_SELECTION="${QWEN38_SPECPREFILL_SELECTION:-$RESULTS/specprefill-selection.json}"
OMLX_MTP_GATE="${QWEN38_OMLX_MTP_GATE:-$RESULTS/omlx-mtp-gate.json}"

MLX_RUNTIME_REVISION="${QWEN38_MLX_RUNTIME_REVISION:-v26.8.9}"
LLAMA_RUNTIME_REVISION="${QWEN38_LLAMA_RUNTIME_REVISION:-v0.2.0/b10566@bb4caa7540188872173c44d161602d9271386413}"
MLX_MODEL_REVISION="${QWEN38_MLX_MODEL_REVISION:-011e38296b3d2aa99245ed49a700459c4ac246b6}"
UNSLOTH_MODEL_REVISION="${QWEN38_UNSLOTH_MODEL_REVISION:-4ca720788d1e01f1bff70c033e0d0028fd02e502}"
MLX_DSPARK_RUNTIME_REVISION="v0.15.0/69cd5c122d19ad3916eefccd43334ff59a92a914"
MLX_DSPARK_MODEL_REVISION="815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"

ACTIVE_PID=""
MACMON_PID=""
MACMON_LOG=""
LAST_RUNTIME_LOG=""

usage() {
  cat >&2 <<'EOF'
usage: run-campaign.sh {smoke|cache-32k|mtp-32k|omlx-smoke|omlx-cache-32k|omlx-mtp-32k|specprefill-16k|specprefill-32k|ane-16k|ane-32k|dspark-smoke|dspark-decode-8k|dspark-cache-32k|dspark-decode-32k|cache-65k|tool-loop|summary|native-262k}
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
    P|Q|R|S)
      RUNTIME="mlx-dspark"
      MODEL_ID="mlx-community/Qwen3.8-27B-8bit"
      RUNTIME_REVISION="$MLX_DSPARK_RUNTIME_REVISION"
      MODEL_REVISION="$MLX_DSPARK_MODEL_REVISION"
      PORT=8484
      LAUNCHER="$SCRIPTS/run-mlx-dspark.sh"
      ;;
    *)
      echo "unknown arm: $arm" >&2
      return 64
      ;;
  esac
  TOKENIZER_PATH=""
  case "$arm" in
    I)
      TOKENIZER_PATH="${OMLX_MODEL_ROOT:-}/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-$MLX_MODEL_REVISION"
      ;;
    J|K|L|M|N|O)
      TOKENIZER_PATH="${OMLX_MODEL_ROOT:-}/True2456-Qwen3.8-27B-AWQ-5.0bpw-dc699a76ddcbef44c188a8aee2ccc79ccc339a04"
      ;;
    P|Q|R|S)
      TOKENIZER_PATH="${MLX_DSPARK_TARGET_PATH:-}"
      ;;
  esac
  API_MODEL="$MODEL_ID"
  if [[ "$RUNTIME" == "oMLX" && -n "$TOKENIZER_PATH" ]]; then
    API_MODEL="$(basename "$TOKENIZER_PATH")"
  fi

  CACHE_ARGS=()
  MTP_ARGS=()
  SPECPREFILL_ARGS=()
  ANE_PREFILL_ARGS=()
  case "$arm" in
    B|C|E|F|G|H|K|L|M|N|Q|R|S) CACHE_ARGS=(--cache-enabled) ;;
  esac
  case "$arm" in
    C|F|G|H) MTP_ARGS=(--mtp-enabled) ;;
    L|M|N) MTP_ARGS=(--mtp-enabled) ;;
  esac
  case "$arm" in
    M) SPECPREFILL_ARGS=(--specprefill=true --specprefill-keep-pct 0.40 --specprefill-threshold 8192 --specprefill-draft-model Qwen/Qwen3.5-2B --specprefill-draft-revision 15852e8c16360a2fea060d615a32b45270f8a8fc) ;;
    N) SPECPREFILL_ARGS=(--specprefill=true --specprefill-keep-pct 0.50 --specprefill-threshold 8192 --specprefill-draft-model Qwen/Qwen3.5-0.8B --specprefill-draft-revision 2fc06364715b967f1860aea9cf38778875588b17) ;;
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

probe_python() {
  if [[ -n "${QWEN38_PROBE_PYTHON:-}" ]]; then
    printf '%s\n' "$QWEN38_PROBE_PYTHON"
    return
  fi
  local runtime_command=""
  case "$RUNTIME" in
    oMLX) runtime_command="${QWEN38_OMLX_BIN:-omlx}" ;;
    mlx-dspark) runtime_command="${MLX_DSPARK_BIN:-mlx-dspark}" ;;
  esac
  if [[ -n "$runtime_command" ]]; then
    local runtime_bin shebang interpreter
    runtime_bin="$(command -v "$runtime_command" 2>/dev/null || true)"
    if [[ -n "$runtime_bin" ]]; then
      IFS= read -r shebang <"$runtime_bin" || true
      interpreter="${shebang#\#!}"
      if [[ "$shebang" == '#!'* && -x "$interpreter" ]]; then
        printf '%s\n' "$interpreter"
        return
      fi
    fi
  fi
  printf '%s\n' python3
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
  local runtime_log="$3"
  local arm="$4"
  local context="$5"
  cleanup
  python3 "$SCRIPTS/enrich_telemetry.py" \
    --results "$results_file" \
    --telemetry "$MACMON_LOG" \
    --session-id "$session_id" \
    --runtime-log "$runtime_log" \
    --arm "$arm" \
    --context "$context"
  if [[ "$INTER_RUN_SECONDS" != "0" ]]; then
    sleep "$INTER_RUN_SECONDS"
  fi
}

validate_mtp_log() {
  local arm="$1"
  local log_file="$2"
  case "$arm" in
    C|F|G|H|L)
      if ! grep -Eiq 'mtp|draft' "$log_file"; then
        echo "arm $arm did not report MTP/draft activation in $log_file" >&2
        return 1
      fi
      ;;
  esac
}

wait_for_cooldown() {
  echo "Thermal cooldown gate: CPU below 38C and GPU below 50C"
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  local attempt sample cpu_temperature gpu_temperature
  for ((attempt = 1; attempt <= 120; attempt++)); do
    sample="$(macmon pipe --samples 1 2>/dev/null)"
    read -r cpu_temperature gpu_temperature < <(jq -er '[.temp.cpu_temp_avg, .temp.gpu_temp_avg] | @tsv' <<<"$sample")
    if awk "BEGIN { exit !($cpu_temperature < 38.0 && $gpu_temperature < 50.0) }"; then
      echo "Thermal sensors ready: CPU=${cpu_temperature}C GPU=${gpu_temperature}C"
      return 0
    fi
    sleep 5
  done
  echo "CPU/GPU sensors did not reach the cooldown thresholds" >&2
  return 1
}

run_cache_arm() {
  local arm="$1"
  local context="$2"
  local content_class="${3:-audit_retrieval}"
  arm_metadata "$arm" || return 1
  echo "RUN arm=$arm context=$context mode=cache"
  wait_for_cooldown || return 1
  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ "$RUNTIME" == "oMLX" || "$RUNTIME" == "mlx-dspark" ]]; then
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
  LAST_RUNTIME_LOG="$runtime_log"
  local session_id="${stamp}-${arm}-${context}-cache"
  start_runtime "$arm" "$context" "$runtime_log" || { cleanup; return 1; }
  wait_for_server "http://127.0.0.1:${PORT}/v1" || { cleanup; return 1; }

  PROBE_COMMAND=(
    "$(probe_python)" "$SCRIPTS/cache_probe.py"
    --base-url "http://127.0.0.1:${PORT}/v1"
    --model "$MODEL_ID"
    --api-model "$API_MODEL"
    --runtime "$RUNTIME"
    --runtime-revision "$RUNTIME_REVISION"
    --model-revision "$MODEL_REVISION"
    --arm "$arm"
    --session-id "$session_id"
    --context "$context"
    --content-class "$content_class"
    --repeat "$REPEATS"
    --output "$RESULTS/cache-probe.jsonl"
  )
  if [[ "$RUNTIME" == "mlx-dspark" ]]; then
    PROBE_COMMAND+=(--mlx-dspark-metrics-url "http://127.0.0.1:${PORT}/metrics" --machine-url "http://127.0.0.1:${PORT}/machine")
    case "$arm" in
      R) PROBE_COMMAND+=(--drafter-id RadixArk/Qwen3.8-27B-DSpark --drafter-revision 85ef153be924f17ce4bf62726954eeaa4a73e854) ;;
      S) PROBE_COMMAND+=(--drafter-id incoai/Qwen3.8-27B-DFlash2 --drafter-revision dedf8df68adfb1afeaf7b7480c0a0243108177b4) ;;
    esac
  else
    PROBE_COMMAND+=(--metrics-url "http://127.0.0.1:${PORT}/metrics")
  fi
  if [[ -n "${TOKENIZER_PATH:-}" ]]; then
    PROBE_COMMAND+=(--tokenizer-path "$TOKENIZER_PATH")
  fi
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
  "${PROBE_COMMAND[@]}" || { cleanup; return 1; }

  validate_mtp_log "$arm" "$runtime_log" || { cleanup; return 1; }
  finish_runtime "$RESULTS/cache-probe.jsonl" "$session_id" "$runtime_log" "$arm" "$context" || return 1
}

run_tool_arm() {
  local arm="$1"
  local context="${2:-32768}"
  arm_metadata "$arm" || return 1
  echo "RUN arm=$arm context=$context mode=tool-loop"
  wait_for_cooldown || return 1
  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ "$RUNTIME" == "oMLX" || "$RUNTIME" == "mlx-dspark" ]]; then
      echo "+ bash $LAUNCHER $arm (tool-loop)"
    else
      bash "$LAUNCHER" "$arm" --print
    fi
    return 0
  fi

  mkdir -p "$RESULTS" "$LOGS"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local runtime_log="$LOGS/${stamp}-${arm}-tool-loop-runtime.log"
  local session_id="${stamp}-${arm}-tool-loop"
  start_runtime "$arm" "$context" "$runtime_log" || { cleanup; return 1; }
  wait_for_server "http://127.0.0.1:${PORT}/v1" || { cleanup; return 1; }

  TOOL_COMMAND=(
    python3 "$SCRIPTS/tool_loop.py"
    --base-url "http://127.0.0.1:${PORT}/v1"
    --model "$MODEL_ID"
    --runtime "$RUNTIME"
    --runtime-revision "$RUNTIME_REVISION"
    --model-revision "$MODEL_REVISION"
    --arm "$arm"
    --session-id "$session_id"
    --context "$context"
    --output "$RESULTS/tool-loop.jsonl"
    --metrics-url "http://127.0.0.1:${PORT}/metrics"
  )
  if [[ "${#CACHE_ARGS[@]}" -gt 0 ]]; then
    TOOL_COMMAND+=("${CACHE_ARGS[@]}")
  fi
  if [[ "${#MTP_ARGS[@]}" -gt 0 ]]; then
    TOOL_COMMAND+=("${MTP_ARGS[@]}")
  fi
  if [[ "${#SPECPREFILL_ARGS[@]}" -gt 0 ]]; then
    TOOL_COMMAND+=("${SPECPREFILL_ARGS[@]}")
  fi
  printf '+ %q ' "${TOOL_COMMAND[@]}"
  printf '\n'
  "${TOOL_COMMAND[@]}" || { cleanup; return 1; }

  validate_mtp_log "$arm" "$runtime_log" || { cleanup; return 1; }
  finish_runtime "$RESULTS/tool-loop.jsonl" "$session_id" "$runtime_log" "$arm" "$context" || return 1
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

specprefill_winner_arm() {
  if [[ ! -f "$SPECPREFILL_SELECTION" ]]; then
    summarize >/dev/null || true
  fi
  jq -r '.winner.arm // empty' "$SPECPREFILL_SELECTION"
}

require_omlx_mtp_gate() {
  if [[ ! -f "$OMLX_MTP_GATE" ]]; then
    summarize >/dev/null || true
  fi
  if [[ ! -f "$OMLX_MTP_GATE" ]] || ! jq -e '.passed == true and .arm == "L"' "$OMLX_MTP_GATE" >/dev/null; then
    echo "SpecPrefill requires a passing isolated L/MTP gate: $OMLX_MTP_GATE" >&2
    return 2
  fi
}

run_omlx_smoke() (
  set +e
  run_cache_arm I 8192
  local arm_i_status=$?
  if [[ "$arm_i_status" -ne 0 ]]; then
    if [[ -n "$LAST_RUNTIME_LOG" ]] && grep -Eiq 'checkpoint.*incompatib|incompatib.*checkpoint' "$LAST_RUNTIME_LOG"; then
      echo "arm I checkpoint incompatibility recorded; continuing with J" >&2
    else
      return "$arm_i_status"
    fi
  fi
  run_cache_arm J 8192
)

run_arms() {
  local context="$1"
  shift
  local arm
  for arm in "$@"; do
    run_cache_arm "$arm" "$context"
  done
}

run_dspark_decode() {
  local context="$1"
  local arm content_class
  local arm_list="${QWEN38_DSPARK_ARMS:-P Q R S}"
  local content_class_list="${QWEN38_DSPARK_CONTENT_CLASSES:-code math chat tool_call_json}"
  arm_list="${arm_list//,/ }"
  content_class_list="${content_class_list//,/ }"
  for arm in $arm_list; do
    case "$arm" in P|Q|R|S) ;; *) echo "invalid mlx-dspark arm filter: $arm" >&2; return 64 ;; esac
    for content_class in $content_class_list; do
      case "$content_class" in
        audit_retrieval|code|math|chat|tool_call_json) ;;
        *) echo "invalid mlx-dspark content-class filter: $content_class" >&2; return 64 ;;
      esac
      run_cache_arm "$arm" "$context" "$content_class"
    done
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
    run_omlx_smoke
    ;;
  omlx-cache-32k)
    run_cache_arm K 32768 code
    ;;
  omlx-mtp-32k)
    run_cache_arm L 32768 code
    run_tool_arm L 32768
    summarize || true
    ;;
  specprefill-16k)
    require_omlx_mtp_gate
    run_arms 16384 L M N
    ;;
  specprefill-32k)
    require_omlx_mtp_gate
    run_arms 32768 L M N
    run_tool_arm M 32768
    run_tool_arm N 32768
    summarize || true
    ;;
  ane-16k)
    run_arms 16384 J O
    ;;
  ane-32k)
    run_arms 32768 J O
    ;;
  dspark-smoke)
    if [[ "$DRY_RUN" == "1" ]]; then
      echo "+ bash $SCRIPTS/run-mlx-dspark.sh auto-smoke"
    else
      bash "$SCRIPTS/run-mlx-dspark.sh" auto-smoke
    fi
    ;;
  dspark-decode-8k)
    run_dspark_decode 8192
    ;;
  dspark-cache-32k)
    run_dspark_decode 32768
    ;;
  dspark-decode-32k)
    run_dspark_decode 32768
    run_tool_arm R 32768
    run_tool_arm S 32768
    ;;
  cache-65k)
    SPECPREFILL_WINNER=""
    if [[ "$DRY_RUN" == "1" ]]; then
      run_arms 65536 C E F G H
      if [[ -f "$SPECPREFILL_SELECTION" ]]; then
        SPECPREFILL_WINNER="$(specprefill_winner_arm)"
        [[ -n "$SPECPREFILL_WINNER" ]] && run_arms 65536 "$SPECPREFILL_WINNER"
      fi
    else
      summarize || true
      ARMS=()
      while IFS= read -r ARM; do
        [[ -n "$ARM" ]] && ARMS+=("$ARM")
      done < <(survivor_arms)
      SPECPREFILL_WINNER="$(specprefill_winner_arm)"
      [[ -n "$SPECPREFILL_WINNER" ]] && ARMS+=("$SPECPREFILL_WINNER")
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
