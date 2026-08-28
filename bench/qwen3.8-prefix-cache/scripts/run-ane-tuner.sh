#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CAMPAIGN="$ROOT/bench/qwen3.8-prefix-cache"
SCRIPTS="$CAMPAIGN/scripts"
CONFIG="$CAMPAIGN/config/omlx-arms.json"
RESULTS="$CAMPAIGN/results"
LOGS="$CAMPAIGN/logs"
OMLX_BIN="${QWEN38_OMLX_BIN:-omlx}"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
MODEL_REVISION="dc699a76ddcbef44c188a8aee2ccc79ccc339a04"
MODEL_KEY="True2456-Qwen3.8-27B-AWQ-5.0bpw-$MODEL_REVISION"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BASE_PATH="$LOGS/omlx/ane-tuner-$STAMP"
RUNTIME_LOG="$LOGS/ane-tuner-$STAMP-runtime.log"
RESULT_PATH="$RESULTS/ane-tuner-result.json"
PROFILE_PATH="$RESULTS/ane-tuner-profile.json"
OMLX_PID=""

cleanup() {
  if [[ -n "$OMLX_PID" ]] && kill -0 "$OMLX_PID" 2>/dev/null; then
    kill "$OMLX_PID" 2>/dev/null || true
    wait "$OMLX_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if screen -ls 2>/dev/null | grep -q 'qwen38-download'; then
  echo "model downloads are active; ANE tuning would contaminate both workloads" >&2
  exit 75
fi
if curl --silent --fail --max-time 1 http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  echo "port 8000 already serves another runtime" >&2
  exit 75
fi
if [[ "$("$OMLX_BIN" --version)" != "0.6.3rc2" ]]; then
  echo "ANE tuner requires pinned oMLX 0.6.3rc2" >&2
  exit 65
fi

echo "Waiting for the campaign thermal baseline before ANE tuning"
for _ in $(seq 1 120); do
  sample="$(macmon pipe --samples 1 2>/dev/null)"
  read -r cpu_temperature gpu_temperature < <(
    jq -er '[.temp.cpu_temp_avg, .temp.gpu_temp_avg] | @tsv' <<<"$sample"
  )
  if awk "BEGIN { exit !($cpu_temperature < 38.0 && $gpu_temperature < 50.0) }"; then
    break
  fi
  sleep 5
done
if ! awk "BEGIN { exit !($cpu_temperature < 38.0 && $gpu_temperature < 50.0) }"; then
  echo "thermal baseline was not reached" >&2
  exit 75
fi

python3 "$SCRIPTS/omlx_config.py" \
  --config "$CONFIG" \
  --arm J \
  --base-path "$BASE_PATH" \
  --model-root "$MODEL_ROOT" \
  --skip-auth

mkdir -p "$LOGS" "$RESULTS"
env \
  OMLX_BASE_PATH="$BASE_PATH" \
  OMLX_MODEL_DIR="$MODEL_ROOT" \
  OMLX_PORT=8000 \
  OMLX_CACHE_ENABLED=false \
  "$OMLX_BIN" serve >"$RUNTIME_LOG" 2>&1 &
OMLX_PID=$!

for _ in $(seq 1 180); do
  if ! kill -0 "$OMLX_PID" 2>/dev/null; then
    echo "oMLX exited before the ANE tuner became healthy: $RUNTIME_LOG" >&2
    exit 1
  fi
  if curl --silent --fail http://127.0.0.1:8000/v1/models >/dev/null; then
    break
  fi
  sleep 1
done
if ! curl --silent --fail http://127.0.0.1:8000/v1/models >/dev/null; then
  echo "oMLX did not become healthy for ANE tuning: $RUNTIME_LOG" >&2
  exit 1
fi

python3 "$SCRIPTS/ane_tuner.py" \
  --base-url http://127.0.0.1:8000 \
  --model-id "$MODEL_KEY" \
  --model-revision "$MODEL_REVISION" \
  --runtime-revision v0.6.3rc2 \
  --sequence-length 2048 \
  --repeats 2 \
  --result "$RESULT_PATH" \
  --profile "$PROFILE_PATH"
