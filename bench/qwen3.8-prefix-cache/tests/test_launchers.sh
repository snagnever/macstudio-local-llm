#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS="$ROOT/bench/qwen3.8-prefix-cache/scripts"

bash -n "$SCRIPTS/run-mlx-serve.sh"
bash -n "$SCRIPTS/run-llama-cpp.sh"
bash -n "$SCRIPTS/run-omlx.sh"
bash -n "$SCRIPTS/run-mlx-dspark.sh"
bash -n "$SCRIPTS/run-campaign.sh"
bash -n "$SCRIPTS/download-models.sh"

MODEL_ROOT="/tmp/qwen38-launcher-fixture"
mkdir -p \
  "$MODEL_ROOT/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-011e38296b3d2aa99245ed49a700459c4ac246b6" \
  "$MODEL_ROOT/True2456-Qwen3.8-27B-AWQ-5.0bpw-dc699a76ddcbef44c188a8aee2ccc79ccc339a04" \
  "$MODEL_ROOT/draft-2b" \
  "$MODEL_ROOT/draft-08b"
MLX_A="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-mlx-serve.sh" A --print)"
MLX_B="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-mlx-serve.sh" B --print)"
MLX_C="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-mlx-serve.sh" C --print)"
GGUF_D="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" D --print)"
GGUF_E="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" E --print)"
GGUF_F="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" F --print)"
GGUF_G="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" G --print)"
GGUF_H="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" H --print)"

ANE_PROFILE="$(mktemp /tmp/qwen38-ane-profile.XXXXXX)"
VERSION_LOG="$(mktemp /tmp/qwen38-omlx-version.XXXXXX)"
FAKE_OMLX_OK="$(mktemp /tmp/qwen38-omlx-ok.XXXXXX)"
FAKE_OMLX_BAD="$(mktemp /tmp/qwen38-omlx-bad.XXXXXX)"
FAKE_DSPARK_OK="$(mktemp /tmp/qwen38-dspark-ok.XXXXXX)"
FAKE_DSPARK_BAD="$(mktemp /tmp/qwen38-dspark-bad.XXXXXX)"
trap 'rm -f "$ANE_PROFILE" "$VERSION_LOG" "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD" "$FAKE_DSPARK_OK" "$FAKE_DSPARK_BAD"' EXIT
printf '%s\n' '{"qwen35_ane_prefill_sequence_length":8192}' >"$ANE_PROFILE"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == "--version" ]]; then' \
  "  printf '%s\\n' checked > '$VERSION_LOG'" \
  "  printf '%s\\n' '0.6.3rc2'" \
  '  exit 0' \
  'fi' \
  '[[ "$1" == "serve" ]]' >"$FAKE_OMLX_OK"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == "--version" ]]; then' \
  "  printf '%s\\n' 'v0.6.2'" \
  '  exit 0' \
  'fi' \
  '[[ "$1" == "serve" ]]' >"$FAKE_OMLX_BAD"
chmod +x "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == "doctor" && "$2" == "--json" ]]; then' \
  '  echo '\''{"ok":true,"environment":{"version":"0.15.0"}}'\''' \
  '  exit 0' \
  'fi' \
  'if [[ "$1" == "serve" ]]; then exit "${FAKE_DSPARK_SERVE_STATUS:-0}"; fi' \
  'exit 64' >"$FAKE_DSPARK_OK"
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'if [[ "$1" == "doctor" && "$2" == "--json" ]]; then' \
  '  echo '\''{"ok":true,"environment":{"version":"0.15.1"}}'\''' \
  '  exit 0' \
  'fi' \
  'exit 64' >"$FAKE_DSPARK_BAD"
chmod +x "$FAKE_DSPARK_OK" "$FAKE_DSPARK_BAD"
OMLX_I="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" I --print)"
OMLX_J="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" J --print)"
OMLX_K="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" K --print)"
OMLX_L="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" L --print)"
OMLX_M="$(OMLX_MODEL_ROOT="$MODEL_ROOT" OMLX_DRAFT_2B_PATH="$MODEL_ROOT/draft-2b" bash "$SCRIPTS/run-omlx.sh" M --print)"
OMLX_N="$(OMLX_MODEL_ROOT="$MODEL_ROOT" OMLX_DRAFT_08B_PATH="$MODEL_ROOT/draft-08b" bash "$SCRIPTS/run-omlx.sh" N --print)"
OMLX_O="$(OMLX_MODEL_ROOT="$MODEL_ROOT" OMLX_ANE_PROFILE="$ANE_PROFILE" bash "$SCRIPTS/run-omlx.sh" O --print)"
mkdir -p "$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" "$MODEL_ROOT/RadixArk--Qwen3.8-27B-DSpark-85ef153be924f17ce4bf62726954eeaa4a73e854" "$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4"
DSPARK_Q="$(MLX_DSPARK_BIN="$FAKE_DSPARK_OK" MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" bash "$SCRIPTS/run-mlx-dspark.sh" Q --print)"
DSPARK_R="$(MLX_DSPARK_BIN="$FAKE_DSPARK_OK" MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" MLX_DSPARK_DSPARK_PATH="$MODEL_ROOT/RadixArk--Qwen3.8-27B-DSpark-85ef153be924f17ce4bf62726954eeaa4a73e854" bash "$SCRIPTS/run-mlx-dspark.sh" R --print)"
DSPARK_S="$(MLX_DSPARK_BIN="$FAKE_DSPARK_OK" MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" MLX_DSPARK_DFLASH2_PATH="$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4" bash "$SCRIPTS/run-mlx-dspark.sh" S --print)"
DSPARK_AUTO="$(MLX_DSPARK_BIN="$FAKE_DSPARK_OK" MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" MLX_DSPARK_DFLASH2_PATH="$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4" bash "$SCRIPTS/run-mlx-dspark.sh" auto-smoke --print)"
grep -q -- '--mode baseline' <<<"$DSPARK_Q"
grep -q -- '--mode dspark' <<<"$DSPARK_R"
grep -q -- '--mode dflash' <<<"$DSPARK_S"
grep -q -- '--max-draft auto' <<<"$DSPARK_R"
grep -q -- '--max-draft auto' <<<"$DSPARK_S"
! grep -q -- '--kv-bits' <<<"$DSPARK_R"
grep -q -- '--mode dflash' <<<"$DSPARK_AUTO"
grep -q -- "--drafter $MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4" <<<"$DSPARK_AUTO"
if MLX_DSPARK_BIN="$FAKE_DSPARK_BAD" MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" bash "$SCRIPTS/run-mlx-dspark.sh" Q --print >/dev/null 2>&1; then
  echo "mlx-dspark launcher accepted an unpinned runtime version" >&2
  exit 1
fi

DSPARK_EARLY_EXIT_LOG="$(mktemp /tmp/qwen38-dspark-early-exit.XXXXXX)"
if FAKE_DSPARK_SERVE_STATUS=73 QWEN38_HEALTH_ATTEMPTS=1 \
  MLX_DSPARK_BIN="$FAKE_DSPARK_OK" \
  MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" \
  MLX_DSPARK_DFLASH2_PATH="$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4" \
  bash "$SCRIPTS/run-mlx-dspark.sh" auto-smoke > /dev/null 2>"$DSPARK_EARLY_EXIT_LOG"; then
  echo "mlx-dspark auto-smoke accepted a child that exited before health" >&2
  exit 1
fi
grep -q -- 'exited before health' "$DSPARK_EARLY_EXIT_LOG"
rm -f "$DSPARK_EARLY_EXIT_LOG"

DSPARK_OCCUPIED_LOG="$(mktemp /tmp/qwen38-dspark-occupied.XXXXXX)"
python3 -c 'import socket, time; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("127.0.0.1", 8484)); s.listen(); time.sleep(30)' >/dev/null 2>&1 &
DSPARK_OCCUPIED_PID=$!
for _ in $(seq 1 20); do
  python3 -c 'import socket, sys; s=socket.socket(); s.settimeout(0.1); status=s.connect_ex(("127.0.0.1", 8484)); s.close(); sys.exit(status)' && break
  sleep 0.05
done
set +e
QWEN38_HEALTH_ATTEMPTS=1 \
  MLX_DSPARK_BIN="$FAKE_DSPARK_OK" \
  MLX_DSPARK_TARGET_PATH="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" \
  MLX_DSPARK_DFLASH2_PATH="$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4" \
  bash "$SCRIPTS/run-mlx-dspark.sh" auto-smoke >/dev/null 2>"$DSPARK_OCCUPIED_LOG"
DSPARK_OCCUPIED_STATUS=$?
set -e
kill "$DSPARK_OCCUPIED_PID" 2>/dev/null || true
wait "$DSPARK_OCCUPIED_PID" 2>/dev/null || true
[[ "$DSPARK_OCCUPIED_STATUS" -ne 0 ]]
grep -q -- 'port 8484 is already in use' "$DSPARK_OCCUPIED_LOG"
rm -f "$DSPARK_OCCUPIED_LOG"

grep -q -- "--model $MODEL_ROOT/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-011e38296b3d2aa99245ed49a700459c4ac246b6" <<<"$MLX_C"
! grep -q -- '--model ddalcu/' <<<"$MLX_C"
grep -q -- '--prefix-cache-entries 0' <<<"$MLX_A"
grep -q -- '--no-mtp' <<<"$MLX_A"
grep -q -- '--no-pld' <<<"$MLX_A"
grep -q -- '--no-mtp' <<<"$MLX_B"
grep -q -- '--no-pld' <<<"$MLX_B"
! grep -q -- '--no-mtp' <<<"$MLX_C"
! grep -q -- '--no-pld' <<<"$MLX_C"
! grep -q -- '--mtp-depth' <<<"$MLX_C"

grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_D"
grep -q -- "-m $MODEL_ROOT/unsloth-Qwen3.8-27B-GGUF-4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-Q4_K_XL.gguf" <<<"$GGUF_D"
! grep -q -- '-hf ' <<<"$GGUF_D"
grep -q -- '--no-cache-prompt' <<<"$GGUF_D"
grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_E"
! grep -q -- '--spec-type' <<<"$GGUF_E"
grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_F"
grep -q -- '--spec-type draft-mtp' <<<"$GGUF_F"
grep -q -- "--spec-draft-model $MODEL_ROOT/unsloth-Qwen3.8-27B-GGUF-4ca720788d1e01f1bff70c033e0d0028fd02e502/MTP/mtp-Qwen3.8-27B-Q4_0.gguf" <<<"$GGUF_F"
! grep -q -- '--spec-draft-model' <<<"$GGUF_E"
grep -q -- 'UD-Q6_K_XL' <<<"$GGUF_G"
grep -q -- 'UD-Q8_K_XL' <<<"$GGUF_H"
grep -q -- 'reasoning_effort.*xhigh' <<<"$GGUF_H"
! grep -q -- 'reasoning_effort.*medium' <<<"$GGUF_H"

grep -q -- 'OMLX_CACHE_ENABLED=false' <<<"$OMLX_I"
grep -q -- 'Qwen3.8-27B-MLX-Serve-8bit' <<<"$OMLX_I"
grep -q -- 'OMLX_CACHE_ENABLED=false' <<<"$OMLX_J"
grep -q -- 'OMLX_CACHE_ENABLED=true' <<<"$OMLX_K"
grep -q -- '"mtp_enabled": true' <<<"$OMLX_L"
grep -q -- '"specprefill_draft_model": ".*/draft-2b"' <<<"$OMLX_M"
grep -q -- '"specprefill_keep_pct": 0.4' <<<"$OMLX_M"
grep -q -- '"specprefill_draft_model": ".*/draft-08b"' <<<"$OMLX_N"
grep -q -- '"specprefill_keep_pct": 0.5' <<<"$OMLX_N"
grep -q -- '"qwen35_ane_prefill_enabled": true' <<<"$OMLX_O"
grep -q -- '"specprefill_enabled": false' <<<"$OMLX_O"
grep -q -- '"mtp_enabled": false' <<<"$OMLX_O"

QWEN38_OMLX_BIN="$FAKE_OMLX_OK" \
  QWEN38_OMLX_RUN_ID="version-ok-$RANDOM" \
  OMLX_MODEL_ROOT="$MODEL_ROOT" \
  bash "$SCRIPTS/run-omlx.sh" J >/dev/null
test -s "$VERSION_LOG"

if QWEN38_OMLX_BIN="$FAKE_OMLX_BAD" OMLX_MODEL_ROOT="$MODEL_ROOT" \
  bash "$SCRIPTS/run-omlx.sh" J >/dev/null 2>&1; then
  echo "oMLX launcher accepted a runtime version other than v0.6.3rc2" >&2
  exit 1
fi

if bash "$SCRIPTS/run-mlx-serve.sh" D --print >/dev/null 2>&1; then
  echo "MLX launcher accepted invalid arm D" >&2
  exit 1
fi

if bash "$SCRIPTS/run-llama-cpp.sh" C --print >/dev/null 2>&1; then
  echo "GGUF launcher accepted invalid arm C" >&2
  exit 1
fi

if OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" M --print >/dev/null 2>&1; then
  echo "oMLX launcher accepted M without a draft path" >&2
  exit 1
fi

if OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" O --print >/dev/null 2>&1; then
  echo "oMLX launcher accepted O without a tuner profile" >&2
  exit 1
fi

for INVALID_RUN_ID in . .. ../.omlx nested/run 'nested\\run'; do
  if QWEN38_OMLX_RUN_ID="$INVALID_RUN_ID" OMLX_MODEL_ROOT="$MODEL_ROOT" \
    bash "$SCRIPTS/run-omlx.sh" J --print >/dev/null 2>&1; then
    echo "oMLX launcher accepted unsafe run ID: $INVALID_RUN_ID" >&2
    exit 1
  fi
done

SMOKE="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" smoke)"
grep -q -- 'Thermal cooldown gate: CPU below 38C and GPU below 50C' <<<"$SMOKE"
grep -q -- 'arm=A context=8192' <<<"$SMOKE"
grep -q -- 'arm=B context=8192' <<<"$SMOKE"
grep -q -- 'arm=D context=8192' <<<"$SMOKE"
grep -q -- 'arm=E context=8192' <<<"$SMOKE"
! grep -q -- 'arm=C context=8192' <<<"$SMOKE"

MTP="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" mtp-32k)"
grep -q -- 'arm=C context=32768' <<<"$MTP"
grep -q -- 'arm=F context=32768' <<<"$MTP"

DSPARK_SMOKE="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" dspark-smoke)"
grep -q -- 'run-mlx-dspark.sh auto-smoke' <<<"$DSPARK_SMOKE"
DSPARK_8K="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" dspark-decode-8k)"
grep -q -- 'arm=R context=8192' <<<"$DSPARK_8K"
grep -q -- 'arm=S context=8192' <<<"$DSPARK_8K"
DSPARK_S_ONLY="$(QWEN38_DRY_RUN=1 QWEN38_DSPARK_ARMS=S QWEN38_DSPARK_CONTENT_CLASSES=audit_retrieval bash "$SCRIPTS/run-campaign.sh" dspark-decode-8k)"
grep -q -- 'arm=S context=8192' <<<"$DSPARK_S_ONLY"
if grep -Eq -- 'arm=(P|Q|R) context=8192' <<<"$DSPARK_S_ONLY"; then
  echo "mlx-dspark MVP filter ran unselected arms" >&2
  exit 1
fi
DSPARK_CACHE="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" dspark-cache-32k)"
grep -q -- 'arm=Q context=32768' <<<"$DSPARK_CACHE"
DSPARK_32K="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" dspark-decode-32k)"
grep -q -- 'arm=S context=32768 mode=tool-loop' <<<"$DSPARK_32K"

MTP_GATE_FIXTURE="$(mktemp /tmp/qwen38-mtp-gate.XXXXXX)"
SPECPREFILL_SELECTION_FIXTURE="$(mktemp /tmp/qwen38-specprefill-selection.XXXXXX)"
trap 'rm -f "$ANE_PROFILE" "$VERSION_LOG" "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD" "$FAKE_DSPARK_OK" "$FAKE_DSPARK_BAD" "$MTP_GATE_FIXTURE" "$SPECPREFILL_SELECTION_FIXTURE"' EXIT
printf '%s\n' '{"arm":"L","passed":true}' >"$MTP_GATE_FIXTURE"
printf '%s\n' '{"winner":{"arm":"M"}}' >"$SPECPREFILL_SELECTION_FIXTURE"
SPECPREFILL="$(QWEN38_DRY_RUN=1 QWEN38_OMLX_MTP_GATE="$MTP_GATE_FIXTURE" bash "$SCRIPTS/run-campaign.sh" specprefill-32k)"
grep -q -- 'arm=M context=32768' <<<"$SPECPREFILL"
grep -q -- 'arm=N context=32768' <<<"$SPECPREFILL"
! grep -q -- 'context=65536' <<<"$SPECPREFILL"
if QWEN38_DRY_RUN=1 QWEN38_OMLX_MTP_GATE=/tmp/missing-qwen38-gate \
  bash "$SCRIPTS/run-campaign.sh" specprefill-16k >/dev/null 2>&1; then
  echo "SpecPrefill ran without a passing isolated L/MTP gate" >&2
  exit 1
fi
CACHE_65K="$(QWEN38_DRY_RUN=1 QWEN38_SPECPREFILL_SELECTION="$SPECPREFILL_SELECTION_FIXTURE" bash "$SCRIPTS/run-campaign.sh" cache-65k)"
grep -q -- 'arm=C context=65536' <<<"$CACHE_65K"
grep -q -- 'arm=M context=65536' <<<"$CACHE_65K"

FALLBACK_LOG="$(mktemp /tmp/qwen38-arm-i-fallback.XXXXXX)"
FALLBACK_FUNCTION="$(mktemp /tmp/qwen38-arm-i-function.XXXXXX)"
FALLBACK_CALLS="$(mktemp /tmp/qwen38-arm-i-calls.XXXXXX)"
trap 'rm -f "$ANE_PROFILE" "$VERSION_LOG" "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD" "$FAKE_DSPARK_OK" "$FAKE_DSPARK_BAD" "$MTP_GATE_FIXTURE" "$SPECPREFILL_SELECTION_FIXTURE" "$FALLBACK_LOG" "$FALLBACK_FUNCTION" "$FALLBACK_CALLS"' EXIT
sed -n '/^run_omlx_smoke()/,/^run_arms()/p' "$SCRIPTS/run-campaign.sh" | sed '$d' >"$FALLBACK_FUNCTION"
(
  # Load the production fallback function, then stub only its runtime boundary.
  source "$FALLBACK_FUNCTION"
  run_cache_arm() {
    printf '%s\n' "$1" >>"$FALLBACK_CALLS"
    if [[ "$1" == "I" ]]; then
      LAST_RUNTIME_LOG="$FALLBACK_LOG"
      return "$I_STATUS"
    fi
    return 0
  }

  printf '%s\n' 'checkpoint incompatibility' >"$FALLBACK_LOG"
  I_STATUS=47
  set +e
  run_omlx_smoke
  allowed_status=$?
  set -e
  [[ "$allowed_status" -eq 0 ]]
  [[ "$(tr '\n' ' ' <"$FALLBACK_CALLS")" == 'I J ' ]]

  : >"$FALLBACK_CALLS"
  printf '%s\n' 'runtime readiness failed' >"$FALLBACK_LOG"
  I_STATUS=48
  set +e
  run_omlx_smoke
  denied_status=$?
  set -e
  [[ "$denied_status" -eq 48 ]]
  [[ "$(tr '\n' ' ' <"$FALLBACK_CALLS")" == 'I ' ]]
)

if QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" unknown-stage >/dev/null 2>&1; then
  echo "campaign runner accepted an unknown stage" >&2
  exit 1
fi

DOWNLOAD_SMOKE="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/download-models.sh" smoke --print)"
grep -q -- 'ddalcu/Qwen3.8-27B-MLX-Serve-8bit.*--revision 011e38296b3d2aa99245ed49a700459c4ac246b6' <<<"$DOWNLOAD_SMOKE"
grep -q -- 'unsloth/Qwen3.8-27B-GGUF.*--revision 4ca720788d1e01f1bff70c033e0d0028fd02e502' <<<"$DOWNLOAD_SMOKE"
grep -q -- 'Qwen3.8-27B-UD-Q4_K_XL.gguf' <<<"$DOWNLOAD_SMOKE"
grep -q -- 'MTP/mtp-Qwen3.8-27B-Q4_0.gguf' <<<"$DOWNLOAD_SMOKE"
! grep -q -- 'Qwen3.8-27B-UD-Q6_K_XL.gguf' <<<"$DOWNLOAD_SMOKE"

DOWNLOAD_ALL="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/download-models.sh" all --print)"
grep -q -- 'Qwen3.8-27B-UD-Q6_K_XL.gguf' <<<"$DOWNLOAD_ALL"
grep -q -- 'Qwen3.8-27B-UD-Q8_K_XL.gguf' <<<"$DOWNLOAD_ALL"
