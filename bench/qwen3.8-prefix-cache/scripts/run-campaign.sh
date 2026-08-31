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
RUNTIME_SURVIVORS="${QWEN38_RUNTIME_SURVIVORS:-$RESULTS/runtime-survivors.json}"
MLX_DSPARK_SELECTION="${QWEN38_MLX_DSPARK_SELECTION:-$RESULTS/mlx-dspark-selection.json}"
OMLX_MTP_GATE="${QWEN38_OMLX_MTP_GATE:-$RESULTS/omlx-mtp-gate.json}"

MLX_RUNTIME_REVISION="${QWEN38_MLX_RUNTIME_REVISION:-v26.8.9}"
LLAMA_RUNTIME_REVISION="${QWEN38_LLAMA_RUNTIME_REVISION:-v0.2.0/b10566@bb4caa7540188872173c44d161602d9271386413}"
MLX_MODEL_REVISION="${QWEN38_MLX_MODEL_REVISION:-011e38296b3d2aa99245ed49a700459c4ac246b6}"
UNSLOTH_MODEL_REVISION="${QWEN38_UNSLOTH_MODEL_REVISION:-4ca720788d1e01f1bff70c033e0d0028fd02e502}"
MLX_DSPARK_RUNTIME_REVISION="v0.15.0/69cd5c122d19ad3916eefccd43334ff59a92a914"
MLX_DSPARK_MODEL_REVISION="815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
OQ8E_MODEL_REVISION="c99e5aad8a478f71c10b9a3dde6709158b690da6"
OQ8E_FP16_MODEL_REVISION="4761782b9455f335292f4d6cb0c89570dff27a11"
OQ4E_MODEL_REVISION="c41ed507f1b16320942a1e9ce340e71d2692dee2"
DFLASH2_MODEL_REVISION="dedf8df68adfb1afeaf7b7480c0a0243108177b4"
MTPLX_RUNTIME_REVISION="v2.9.2/bbc67427e88288001e4b90ecb44708dc0222154c"
MTPLX_MODEL_REVISION="123db8bcc7101455b00d9aad36c0e760c6e7de02"
MTPLX_QUALITY_MODEL_REVISION="09f71b39a75c416be3c974840b53f9fbe9aa1841"
MTPLX_QUALITY_FP16_MODEL_REVISION="4b3533770e01217f9b523f337b4597fd4ca50eea"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
CAMPAIGN_MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
OMLX_MODEL_ROOT="${OMLX_MODEL_ROOT:-$CAMPAIGN_MODEL_ROOT}"
export OMLX_MODEL_ROOT

ACTIVE_PID=""
MACMON_PID=""
MACMON_LOG=""
LAST_RUNTIME_LOG=""

usage() {
  cat >&2 <<'EOF'
usage: run-campaign.sh {smoke|cache-32k|mtp-32k|omlx-smoke|omlx-cache-32k|omlx-mtp-32k|omlx-mtp-tool-loop-32k|omlx-oq8e-smoke|omlx-oq4e-dflash-32k|mtplx-smoke|mtplx-32k|mtplx-tool-loop-32k|mtplx-quality-smoke|mtplx-quality-32k|specprefill-16k|specprefill-32k|ane-16k|ane-32k|dspark-smoke|dspark-decode-8k|dspark-cache-32k|dspark-decode-32k|dspark-tool-loop-32k|cache-65k|cache-65k-frontrunners|cache-65k-mtplx8|cache-65k-oq8e|mtplx-bank-test|mtplx-toolturn-ab|mtplx-y-recap-128k|cache-128k-mtplx-292|cache-128k-mtplx-2100|cache-262k-mtplx-2100|cache-128k-sweep|cache-262k-sweep|tool-loop|summary|native-262k}
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
    T)
      RUNTIME="oMLX"
      MODEL_ID="Jundot/Qwen3.8-27B-oQ8e-mtp"
      RUNTIME_REVISION="v0.6.3rc2"
      MODEL_REVISION="$OQ8E_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-omlx.sh"
      ;;
    U)
      RUNTIME="oMLX"
      MODEL_ID="Jundot/Qwen3.8-27B-oQ8e-fp16-mtp"
      RUNTIME_REVISION="v0.6.3rc2"
      MODEL_REVISION="$OQ8E_FP16_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-omlx.sh"
      ;;
    W|X)
      RUNTIME="oMLX"
      MODEL_ID="gcoli/Qwen3.8-27B-oQ4e-mtp"
      RUNTIME_REVISION="v0.6.3rc2"
      MODEL_REVISION="$OQ4E_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-omlx.sh"
      ;;
    FN)
      RUNTIME="oMLX"
      MODEL_ID="Jundot/Qwen3.8-Flash-Next-oQ4e-mtp"
      RUNTIME_REVISION="v0.6.4"
      MODEL_REVISION="2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-omlx.sh"
      ;;
    V)
      RUNTIME="MTPLX"
      MODEL_ID="Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed"
      RUNTIME_REVISION="$MTPLX_RUNTIME_REVISION"
      MODEL_REVISION="$MTPLX_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-mtplx.sh"
      ;;
    Y)
      RUNTIME="MTPLX"
      MODEL_ID="Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality"
      RUNTIME_REVISION="$MTPLX_RUNTIME_REVISION"
      MODEL_REVISION="$MTPLX_QUALITY_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-mtplx.sh"
      ;;
    Z)
      RUNTIME="MTPLX"
      MODEL_ID="Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality-FP16"
      RUNTIME_REVISION="$MTPLX_RUNTIME_REVISION"
      MODEL_REVISION="$MTPLX_QUALITY_FP16_MODEL_REVISION"
      PORT=8000
      LAUNCHER="$SCRIPTS/run-mtplx.sh"
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
    T)
      TOKENIZER_PATH="${OMLX_MODEL_ROOT:-}/Jundot-Qwen3.8-27B-oQ8e-mtp-$OQ8E_MODEL_REVISION"
      ;;
    U)
      TOKENIZER_PATH="${OMLX_MODEL_ROOT:-}/Jundot-Qwen3.8-27B-oQ8e-fp16-mtp-$OQ8E_FP16_MODEL_REVISION"
      ;;
    W|X)
      TOKENIZER_PATH="${OMLX_MODEL_ROOT:-}/gcoli-Qwen3.8-27B-oQ4e-mtp-$OQ4E_MODEL_REVISION"
      ;;
    FN)
      TOKENIZER_PATH="${OMLX_MODEL_ROOT:-}/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
      ;;
    V)
      TOKENIZER_PATH="$CAMPAIGN_MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-$MTPLX_MODEL_REVISION"
      ;;
    Y)
      TOKENIZER_PATH="$CAMPAIGN_MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Quality-$MTPLX_QUALITY_MODEL_REVISION"
      ;;
    Z)
      TOKENIZER_PATH="$CAMPAIGN_MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Quality-FP16-$MTPLX_QUALITY_FP16_MODEL_REVISION"
      ;;
    P|Q|R|S)
      TOKENIZER_PATH="${MLX_DSPARK_TARGET_PATH:-}"
      ;;
  esac
  API_MODEL="$MODEL_ID"
  if [[ "$RUNTIME" == "oMLX" && -n "$TOKENIZER_PATH" ]]; then
    API_MODEL="$(basename "$TOKENIZER_PATH")"
  elif [[ "$RUNTIME" == "MTPLX" ]]; then
    API_MODEL="mtplx"
  fi

  CACHE_ARGS=()
  MTP_ARGS=()
  SPECPREFILL_ARGS=()
  ANE_PREFILL_ARGS=()
  SAMPLING_ARGS=()
  case "$arm" in
    B|C|E|F|G|H|K|L|M|N|Q|R|S|T|U|V|Y|Z) CACHE_ARGS=(--cache-enabled) ;;
  esac
  case "$arm" in
    C|F|G|H) MTP_ARGS=(--mtp-enabled) ;;
    L|M|N|T|U|V|Y|Z) MTP_ARGS=(--mtp-enabled) ;;
  esac
  case "$arm" in
    M) SPECPREFILL_ARGS=(--specprefill=true --specprefill-keep-pct 0.40 --specprefill-threshold 8192 --specprefill-draft-model Qwen/Qwen3.5-2B --specprefill-draft-revision 15852e8c16360a2fea060d615a32b45270f8a8fc) ;;
    N) SPECPREFILL_ARGS=(--specprefill=true --specprefill-keep-pct 0.50 --specprefill-threshold 8192 --specprefill-draft-model Qwen/Qwen3.5-0.8B --specprefill-draft-revision 2fc06364715b967f1860aea9cf38778875588b17) ;;
    J|K|L|O|T|U|W|X|Y|Z) SPECPREFILL_ARGS=(--specprefill=false) ;;
  esac
  case "$arm" in
    O) ANE_PREFILL_ARGS=(--ane-prefill-enabled) ;;
  esac
  case "$arm" in
    A|B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z)
      SAMPLING_ARGS=(--temperature 1.0 --top-p 0.95 --top-k 20 --reasoning-effort xhigh)
      ;;
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
    MTPLX) runtime_command="${QWEN38_MTPLX_BIN:-mtplx}" ;;
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
    C|F|G|H|L|T|U|V|X|Y|Z)
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
  local measurement_mode="${4:-performance}"
  arm_metadata "$arm" || return 1
  local run_repeats="$REPEATS"
  # Diagnostic A/B hook: write to an alternate file and/or a scenario subset
  # without touching the canonical results/cache-probe.jsonl dataset.
  local out_file="${QWEN38_CACHE_OUTPUT:-$RESULTS/cache-probe.jsonl}"
  case "$measurement_mode" in
    performance) ;;
    greedy)
      if [[ "$RUNTIME" != "mlx-dspark" ]]; then
        echo "greedy control is only supported for mlx-dspark arms" >&2
        return 64
      fi
      SAMPLING_ARGS=(--temperature 0 --top-p 0.95 --top-k 20 --reasoning-effort xhigh)
      run_repeats=1
      ;;
    *)
      echo "invalid measurement mode: $measurement_mode" >&2
      return 64
      ;;
  esac
  echo "RUN arm=$arm context=$context mode=cache measurement=$measurement_mode repeats=$run_repeats"
  wait_for_cooldown || return 1
  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ "$RUNTIME" == "oMLX" ]]; then
      echo "+ OMLX_MODEL_ROOT=$OMLX_MODEL_ROOT QWEN38_CTX_SIZE=$context bash $LAUNCHER $arm"
    elif [[ "$RUNTIME" == "mlx-dspark" || "$RUNTIME" == "MTPLX" ]]; then
      echo "+ QWEN38_CTX_SIZE=$context bash $LAUNCHER $arm"
    else
      bash "$LAUNCHER" "$arm" --print
    fi
    return 0
  fi

  mkdir -p "$RESULTS" "$LOGS"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local runtime_log="$LOGS/${stamp}-${arm}-${context}-${measurement_mode}-runtime.log"
  LAST_RUNTIME_LOG="$runtime_log"
  local session_id="${stamp}-${arm}-${context}-${measurement_mode}-cache"
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
    --repeat "$run_repeats"
    --output "$out_file"
  )
  if [[ -n "${QWEN38_CACHE_SCENARIOS:-}" ]]; then
    PROBE_COMMAND+=(--scenarios "$QWEN38_CACHE_SCENARIOS")
  fi
  if [[ -n "${QWEN38_SCENARIO_REPEATS:-}" ]]; then
    PROBE_COMMAND+=(--scenario-repeats "$QWEN38_SCENARIO_REPEATS")
  fi
  if [[ -n "${QWEN38_CACHE_SCENARIO_ORDER:-}" ]]; then
    PROBE_COMMAND+=(--scenario-order "$QWEN38_CACHE_SCENARIO_ORDER")
  fi
  if [[ "$RUNTIME" == "mlx-dspark" ]]; then
    PROBE_COMMAND+=(--mlx-dspark-metrics-url "http://127.0.0.1:${PORT}/metrics" --machine-url "http://127.0.0.1:${PORT}/machine")
    case "$arm" in
      R) PROBE_COMMAND+=(--drafter-id RadixArk/Qwen3.8-27B-DSpark --drafter-revision 85ef153be924f17ce4bf62726954eeaa4a73e854) ;;
      S) PROBE_COMMAND+=(--drafter-id incoai/Qwen3.8-27B-DFlash2 --drafter-revision dedf8df68adfb1afeaf7b7480c0a0243108177b4) ;;
    esac
  else
    PROBE_COMMAND+=(--metrics-url "http://127.0.0.1:${PORT}/metrics")
    if [[ "$arm" == "X" ]]; then
      PROBE_COMMAND+=(--drafter-id incoai/Qwen3.8-27B-DFlash2 --drafter-revision "$DFLASH2_MODEL_REVISION")
    fi
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
  if [[ "${#SAMPLING_ARGS[@]}" -gt 0 ]]; then
    PROBE_COMMAND+=("${SAMPLING_ARGS[@]}")
  fi
  printf '+ %q ' "${PROBE_COMMAND[@]}"
  printf '\n'
  "${PROBE_COMMAND[@]}" || { cleanup; return 1; }

  validate_mtp_log "$arm" "$runtime_log" || { cleanup; return 1; }
  finish_runtime "$out_file" "$session_id" "$runtime_log" "$arm" "$context" || return 1
}

run_tool_arm() {
  local arm="$1"
  local context="${2:-32768}"
  arm_metadata "$arm" || return 1
  echo "RUN arm=$arm context=$context mode=tool-loop"
  wait_for_cooldown || return 1
  if [[ "$DRY_RUN" == "1" ]]; then
    if [[ "$RUNTIME" == "oMLX" || "$RUNTIME" == "mlx-dspark" || "$RUNTIME" == "MTPLX" ]]; then
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

  # Best-of-N majority: the tool-loop final-recall contract is non-deterministic at
  # temperature=1.0, so one sampling miss must not fail the whole gate. Run N loops
  # against the same warm runtime and require a majority to pass. Same session-id
  # across repeats keeps one telemetry window for enrich_telemetry.
  local tool_loop_repeats="${QWEN38_TOOL_LOOP_REPEATS:-3}"
  local tool_loop_majority=$(( tool_loop_repeats / 2 + 1 ))
  local tool_loop_passes=0
  local tool_loop_r
  for (( tool_loop_r = 1; tool_loop_r <= tool_loop_repeats; tool_loop_r++ )); do
    TOOL_COMMAND=(
      python3 "$SCRIPTS/tool_loop.py"
      --base-url "http://127.0.0.1:${PORT}/v1"
      --model "$MODEL_ID"
      --api-model "$API_MODEL"
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
    if [[ "${#SAMPLING_ARGS[@]}" -gt 0 ]]; then
      TOOL_COMMAND+=("${SAMPLING_ARGS[@]}")
    fi
    printf '+ %q ' "${TOOL_COMMAND[@]}"
    printf '\n'
    if "${TOOL_COMMAND[@]}"; then
      tool_loop_passes=$(( tool_loop_passes + 1 ))
      echo "tool-loop $arm r${tool_loop_r}: PASS"
    else
      echo "tool-loop $arm r${tool_loop_r}: FAIL"
    fi
  done
  echo "tool-loop $arm majority: ${tool_loop_passes}/${tool_loop_repeats} pass (need ${tool_loop_majority})"
  if (( tool_loop_passes < tool_loop_majority )); then
    echo "tool-loop $arm did not reach majority pass" >&2
    cleanup
    return 1
  fi

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
  if [[ ! -f "$RUNTIME_SURVIVORS" && "$DRY_RUN" == "1" ]]; then
    printf '%s\n' C E F G H
    return 0
  fi
  if [[ ! -f "$RUNTIME_SURVIVORS" ]]; then
    summarize >/dev/null
  fi
  jq -r '.survivors[] | select(.passed == true) | .arm' \
    "$RUNTIME_SURVIVORS"
}

specprefill_winner_arm() {
  if [[ ! -f "$SPECPREFILL_SELECTION" ]]; then
    summarize >/dev/null || true
  fi
  if [[ -f "$SPECPREFILL_SELECTION" ]]; then
    local winner
    winner="$(jq -r '.winner.arm // empty' "$SPECPREFILL_SELECTION")"
    if [[ -n "$winner" ]]; then
      printf '%s\n' "$winner"
      return 0
    fi
  fi

  # A rejected SpecPrefill profile does not invalidate its passing MTP baseline.
  if [[ -f "$OMLX_MTP_GATE" ]] && \
      jq -e '.passed == true and .arm == "L"' "$OMLX_MTP_GATE" >/dev/null; then
    printf '%s\n' L
  fi
}

dspark_winner_arm() {
  if [[ ! -f "$MLX_DSPARK_SELECTION" ]]; then
    summarize >/dev/null || true
  fi
  [[ -f "$MLX_DSPARK_SELECTION" ]] || return 0
  jq -r 'if .winner.selected == true then .winner.arm // empty else empty end' \
    "$MLX_DSPARK_SELECTION"
}

approved_arms() {
  {
    survivor_arms
    specprefill_winner_arm
    dspark_winner_arm
  } | awk 'NF && !seen[$0]++'
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

run_dspark_performance() {
  local context="$1"
  local default_arms="${2:-Q R S}"
  local default_content_classes="${3:-code math chat tool_call_json}"
  local arm content_class
  local arm_list="${QWEN38_DSPARK_ARMS:-$default_arms}"
  local content_class_list="${QWEN38_DSPARK_CONTENT_CLASSES:-$default_content_classes}"
  arm_list="${arm_list//,/ }"
  content_class_list="${content_class_list//,/ }"
  for arm in $arm_list; do
    case "$arm" in P|Q|R|S) ;; *) echo "invalid mlx-dspark arm filter: $arm" >&2; return 64 ;; esac
    for content_class in $content_class_list; do
      case "$content_class" in
        audit_retrieval|code|math|chat|tool_call_json) ;;
        *) echo "invalid mlx-dspark content-class filter: $content_class" >&2; return 64 ;;
      esac
      run_cache_arm "$arm" "$context" "$content_class" performance
    done
  done
}

run_dspark_greedy_control() {
  local context="$1"
  local arm
  local arm_list="${QWEN38_DSPARK_ARMS:-Q R S}"
  arm_list="${arm_list//,/ }"
  for arm in $arm_list; do
    case "$arm" in
      Q|R|S) run_cache_arm "$arm" "$context" code greedy ;;
      P) ;;
      *) echo "invalid mlx-dspark arm filter: $arm" >&2; return 64 ;;
    esac
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
  omlx-mtp-tool-loop-32k)
    run_tool_arm L 32768
    summarize || true
    ;;
  omlx-oq8e-smoke)
    run_arms 32768 T U
    ;;
  omlx-oq4e-dflash-32k)
    run_arms 32768 W X
    ;;
  mtplx-smoke)
    run_cache_arm V 8192 code
    ;;
  mtplx-32k)
    run_cache_arm V 32768 code
    run_tool_arm V 32768
    ;;
  mtplx-tool-loop-32k)
    run_tool_arm V 32768
    ;;
  mtplx-quality-smoke)
    run_cache_arm Y 8192 code
    run_cache_arm Z 8192 code
    ;;
  mtplx-quality-32k)
    # Tool loop a temp=1.0 é flaky (contrato de 4 strings exatas). Aqui ele é
    # comparativo, não gate: registra a maioria mas NÃO aborta o estágio, para
    # o Z sempre ser medido. Rode com QWEN38_TOOL_LOOP_REPEATS=5 p/ maioria estável.
    run_cache_arm Y 32768 code
    run_tool_arm Y 32768 || echo "tool-loop Y não fez maioria (comparativo, seguindo)" >&2
    run_cache_arm Z 32768 code
    run_tool_arm Z 32768 || echo "tool-loop Z não fez maioria (comparativo, seguindo)" >&2
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
    run_dspark_greedy_control 8192
    run_dspark_performance 8192
    ;;
  dspark-cache-32k)
    run_dspark_performance 32768 "P Q" audit_retrieval
    ;;
  dspark-decode-32k)
    run_dspark_greedy_control 32768
    run_dspark_performance 32768
    run_tool_arm R 32768
    run_tool_arm S 32768
    ;;
  cache-65k-frontrunners)
    # Contexto longo (65K) nos front-runners, roteados por run_cache_arm ao runtime
    # de cada braço (L/T=oMLX, V=MTPLX, S=mlx-dspark). Tolerante: um braço que falhar
    # não bloqueia os outros. S exige MLX_DSPARK_* no ambiente.
    run_cache_arm L 65536 || echo "L 65K falhou (seguindo)" >&2
    run_cache_arm T 65536 || echo "T 65K falhou (seguindo)" >&2
    run_cache_arm V 65536 || echo "V 65K falhou (seguindo)" >&2
    run_cache_arm S 65536 || echo "S 65K falhou (seguindo)" >&2
    summarize || true
    ;;
  mtplx-bank-test)
    # Valida a correção do cache MTPLX a 128K. O cap do session-bank (24G/sessão padrão)
    # estoura com KV de 128K -> append/tool_turn re-prefilam. Sobe o cap via
    # MTPLX_SESSION_BANK_PER_SESSION_BYTES / _MAX_BYTES (exportados no launch). Isola a
    # variável: só o cap muda vs cache-128k-sweep. SEM summarize (não misturar caps na média).
    run_cache_arm V 131072 || echo "V 128K (bank test) falhou (seguindo)" >&2
    ;;
  mtplx-toolturn-ab)
    # A/B do achado aberto: tool_turn @128K re-prefila no MTPLX mesmo com o cap subido,
    # enquanto append (estrutura quase igual) reusa. Hipotese: tratamento de tool-history
    # no session-bank/gate de canonicalizacao mudou na 2.9.2 (passthrough por padrao).
    # Braco A = runtime apontado por QWEN38_MTPLX_BIN (2.9.2). Controle B = dados 2.9.1 ja medidos.
    # Grava em arquivo separado (QWEN38_CACHE_OUTPUT) p/ nao poluir o dataset canonico.
    # Roda so append (controle positivo: base reusa) + tool_turn (a questao).
    run_cache_arm V 131072 || echo "V 128K (toolturn A/B) falhou (seguindo)" >&2
    ;;
  cache-128k-mtplx-292)
    # Re-mede V e Y @128K na MTPLX 2.9.2 (release adotada; passthrough por padrão corrige o
    # tool_turn que a 2.9.1 re-prefilava). 5 cenários, 3 repetições (igual a L/T/S@128K, linha
    # uniforme). Cap do session-bank subido no launch. Substitui as sessões 2.9.1 poluídas de
    # V/Y@128K (descartadas na higiene depois). SEM summarize aqui.
    run_cache_arm V 131072 || echo "V 128K (2.9.2) falhou (seguindo)" >&2
    run_cache_arm Y 131072 || echo "Y 128K (2.9.2) falhou (seguindo)" >&2
    ;;
  mtplx-y-recap-128k)
    # Re-mede Y (MTPLX 8-bit) @128K com o cap do session-bank subido (env no launch),
    # para casar com o V corrigido no dashboard. SEM summarize (higiene: a sessão antiga
    # do Y@128K, cap padrão, é descartada depois).
    run_cache_arm Y 131072 || echo "Y 128K (recap) falhou (seguindo)" >&2
    ;;
  cache-128k-sweep)
    # Varredura de contexto (128K) nos front-runners L/T/V/Y/S. 5 cenários, 3 repetições.
    # Degrau intermediário da curva desempenho-vs-contexto até o máximo do modelo (262K).
    # Requer disco livre p/ o transbordo SSD do oMLX (ver anomalia T@65K). S exige MLX_DSPARK_*.
    run_cache_arm L 131072 || echo "L 128K falhou (seguindo)" >&2
    run_cache_arm T 131072 || echo "T 128K falhou (seguindo)" >&2
    run_cache_arm V 131072 || echo "V 128K falhou (seguindo)" >&2
    run_cache_arm Y 131072 || echo "Y 128K falhou (seguindo)" >&2
    run_cache_arm S 131072 || echo "S 128K falhou (seguindo)" >&2
    summarize || true
    ;;
  cache-262k-sweep)
    # Varredura de contexto no MÁXIMO do modelo (262144, nativo). Front-runners L/T/V/Y/S.
    # Corte por-cenário: cold/middle_mutation/tool_turn com 1 rep, identical/append com 2.
    # cold/middle/tool_turn a 262K são re-prefill cheio determinístico (spread <=0.5% a 128K;
    # tool_turn em ordem canônica cai após o middle = pior caso, sempre re-prefila), então 1 rep
    # basta. cold roda primeiro (SCENARIOS) e semeia o bank. Braços MTPLX (V/Y) na 2.9.2.
    # Subset de braços por QWEN38_262K_ARMS (default todos). Tolerante.
    REPEATS=2
    # Corte por-runtime. oMLX/dspark reusam identical/append barato (cache content-addressed),
    # então mantêm 2 reps. MTPLX re-prefila no prime a cada rep (identical leva ~1 prefill cheio),
    # e o hit é determinístico (identical=1.0, append=0.99 estáveis) -> 1 rep. cold/middle/tool_turn
    # = 1 rep em todos (re-prefill determinístico; tool_turn canônico cai após o middle = pior caso).
    cut_default="cold=1,middle_mutation=1,tool_turn=1"
    cut_mtplx="cold=1,middle_mutation=1,tool_turn=1,identical=1,append=1"
    for arm262 in ${QWEN38_262K_ARMS:-L T V Y S}; do
      case "$arm262" in
        V|Y|Z) export QWEN38_SCENARIO_REPEATS="${QWEN38_SCENARIO_REPEATS_MTPLX:-$cut_mtplx}" ;;
        *)     export QWEN38_SCENARIO_REPEATS="${QWEN38_SCENARIO_REPEATS_DEFAULT:-$cut_default}" ;;
      esac
      run_cache_arm "$arm262" 262144 || echo "$arm262 262K falhou (seguindo)" >&2
    done
    summarize || true
    ;;
  cache-65k-oq8e)
    # Re-teste do oQ8e (T) a 65K após liberar disco. A 1ª medição deu cache hit 0
    # por FALHA DE TRANSBORDO PARA SSD (disk_free=1.70 GB): o KV de 65K do oQ8e
    # (8.6 bpw) não coube no SSD cheio. Com disco liberado, isola a variável.
    run_cache_arm T 65536 || echo "T 65K falhou (seguindo)" >&2
    summarize || true
    ;;
  cache-65k-mtplx8)
    # Contexto longo (65K) do MTPLX 8-bit (Y). Complementa V (4-bit) do estágio
    # cache-65k-frontrunners: mede warm cache e throughput da precisão 8-bit,
    # em vez de inferir por analogia com o V. Mesma engine MTPLX, porta 8000.
    run_cache_arm Y 65536 || echo "Y 65K falhou (seguindo)" >&2
    summarize || true
    ;;
  dspark-tool-loop-32k)
    # Só os tool loops R/S a 32K (decode/baseline já medidos noutro estágio).
    # Tolerante: mede os dois mesmo se um não fizer maioria. Rode com
    # QWEN38_TOOL_LOOP_REPEATS=3 para não custar horas a 32K.
    run_tool_arm R 32768 || echo "tool-loop R não fez maioria (seguindo p/ S)" >&2
    run_tool_arm S 32768 || echo "tool-loop S não fez maioria (seguindo)" >&2
    summarize || true
    ;;
  cache-65k)
    [[ "$DRY_RUN" == "1" ]] || summarize || true
    ARMS=()
    while IFS= read -r ARM; do
      [[ -n "$ARM" ]] && ARMS+=("$ARM")
    done < <(approved_arms)
    if [[ "${#ARMS[@]}" -eq 0 ]]; then
      echo "no approved arms are available for 65K" >&2
      exit 2
    fi
    run_arms 65536 "${ARMS[@]}"
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
    [[ "$DRY_RUN" == "1" ]] || summarize || true
    ARMS=()
    while IFS= read -r ARM; do
      [[ -n "$ARM" ]] && ARMS+=("$ARM")
    done < <(approved_arms)
    if [[ "${#ARMS[@]}" -eq 0 ]]; then
      echo "no approved arms are available for native 262K" >&2
      exit 2
    fi
    REPEATS=1
    run_arms 262144 "${ARMS[@]}"
    ;;
  cache-128k-mtplx-2100)
    # Re-probe da campanha runtime-refresh (ver plan-runtime-refresh.md). Re-mede V e Y
    # @128K na MTPLX 2.10.0 com o memory-planning automático (cap DEFAULT, sem override).
    # Isola uma variável: só a versão do runtime muda vs cache-128k-sweep (2.9.2, default,
    # que perdeu append/tool_turn). Testa R2: o planning automático mata o cap-artifact?
    # Grava num arquivo separado p/ não misturar com o dataset 2.9.2. SEM summarize.
    export QWEN38_MTPLX_EXPECTED_VERSION=2.10.0
    export QWEN38_CACHE_OUTPUT="${QWEN38_CACHE_OUTPUT:-$RESULTS/runtime-refresh/cache-probe-mtplx2100.jsonl}"
    MTPLX_RUNTIME_REVISION="v2.10.0/e979b569288286f49440532de4aec9108e0a9e73"
    # Subconjunto de braços via QWEN38_REFRESH_128K_ARMS (default V Y). Ex: "V" p/ resposta rápida.
    for armR in ${QWEN38_REFRESH_128K_ARMS:-V Y}; do
      run_cache_arm "$armR" 131072 || echo "$armR 128K (2.10.0) falhou (seguindo)" >&2
    done
    ;;
  cache-262k-mtplx-2100)
    # Re-probe runtime-refresh a 262K (máximo nativo). Testa R1: o "memory-aware ceiling"
    # da 2.10.0 recupera o decode denso que colapsava (~7 tps) na 2.9.2? Mesmo corte por
    # cenário do cache-262k-sweep p/ MTPLX (identical/append 1 rep; re-prefill determinístico).
    export QWEN38_MTPLX_EXPECTED_VERSION=2.10.0
    export QWEN38_CACHE_OUTPUT="${QWEN38_CACHE_OUTPUT:-$RESULTS/runtime-refresh/cache-probe-mtplx2100.jsonl}"
    export QWEN38_SCENARIO_REPEATS="${QWEN38_SCENARIO_REPEATS_MTPLX:-cold=1,middle_mutation=1,tool_turn=1,identical=1,append=1}"
    MTPLX_RUNTIME_REVISION="v2.10.0/e979b569288286f49440532de4aec9108e0a9e73"
    REPEATS=1
    for armR in ${QWEN38_REFRESH_262K_ARMS:-V Y}; do
      run_cache_arm "$armR" 262144 || echo "$armR 262K (2.10.0) falhou (seguindo)" >&2
    done
    ;;
  refresh-omlx-t-32k)
    # R3 mínimo (runtime-refresh): arm T (oQ8e-mtp) @32K no oMLX novo (Lightning MTP).
    # Mesmo config (mtp_enabled:true); só a versão do runtime muda vs baseline 0.6.3rc2
    # (decode 30.57). Cold, 1 rep. Requer QWEN38_OMLX_EXPECTED_VERSION do launcher.
    run_cache_arm T 32768 || echo "T 32K refresh falhou (seguindo)" >&2
    ;;
  refresh-flashnext-32k)
    # R5 mínimo: Flash-Next 125B-A6B (arm FN) @32K no oMLX 0.6.4 (oQ4e-mtp, Lightning MTP +
    # sparse prefill + SSD-map do PLE). Smoke de velocidade vs a densa. Requer
    # QWEN38_OMLX_EXPECTED_VERSION=0.6.4 e o modelo baixado no OMLX_MODEL_ROOT.
    run_cache_arm FN 32768 || echo "FN 32K (Flash-Next) falhou (seguindo)" >&2
    ;;
  refresh-flashnext-128k)
    # R5 contexto longo: Flash-Next @128K no oMLX 0.6.4 com qwen4_ple_ssd_offload (PLE em mmap ->
    # ~70GB residente, cabe com o KV de 128K). Requer QWEN38_OMLX_EXPECTED_VERSION=0.6.4.
    run_cache_arm FN 131072 || echo "FN 128K (Flash-Next) falhou (seguindo)" >&2
    ;;
  refresh-dspark-s-32k)
    # R4 mínimo (runtime-refresh): arm S (8bit + DFlash2) @32K no mlx-dspark 0.17.2
    # (cap DFlash dinâmico) vs baseline 0.15.0 (decode 39.9). Cold, 1 rep. Requer
    # MLX_DSPARK_TARGET_PATH / MLX_DSPARK_DFLASH2_PATH e QWEN38_MLX_DSPARK_EXPECTED_VERSION.
    run_cache_arm S 32768 || echo "S 32K refresh falhou (seguindo)" >&2
    ;;
  *)
    usage
    exit 64
    ;;
esac
