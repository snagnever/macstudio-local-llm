#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS="$ROOT/bench/qwen3.8-prefix-cache/scripts"

bash -n "$SCRIPTS/run-mlx-serve.sh"
bash -n "$SCRIPTS/run-llama-cpp.sh"
bash -n "$SCRIPTS/run-omlx.sh"
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
trap 'rm -f "$ANE_PROFILE" "$VERSION_LOG" "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD"' EXIT
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
OMLX_I="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" I --print)"
OMLX_J="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" J --print)"
OMLX_K="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" K --print)"
OMLX_L="$(OMLX_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-omlx.sh" L --print)"
OMLX_M="$(OMLX_MODEL_ROOT="$MODEL_ROOT" OMLX_DRAFT_2B_PATH="$MODEL_ROOT/draft-2b" bash "$SCRIPTS/run-omlx.sh" M --print)"
OMLX_N="$(OMLX_MODEL_ROOT="$MODEL_ROOT" OMLX_DRAFT_08B_PATH="$MODEL_ROOT/draft-08b" bash "$SCRIPTS/run-omlx.sh" N --print)"
OMLX_O="$(OMLX_MODEL_ROOT="$MODEL_ROOT" OMLX_ANE_PROFILE="$ANE_PROFILE" bash "$SCRIPTS/run-omlx.sh" O --print)"

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
grep -q -- 'GPU cooldown gate: below 50C' <<<"$SMOKE"
grep -q -- 'arm=A context=8192' <<<"$SMOKE"
grep -q -- 'arm=B context=8192' <<<"$SMOKE"
grep -q -- 'arm=D context=8192' <<<"$SMOKE"
grep -q -- 'arm=E context=8192' <<<"$SMOKE"
! grep -q -- 'arm=C context=8192' <<<"$SMOKE"

MTP="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" mtp-32k)"
grep -q -- 'arm=C context=32768' <<<"$MTP"
grep -q -- 'arm=F context=32768' <<<"$MTP"

MTP_GATE_FIXTURE="$(mktemp /tmp/qwen38-mtp-gate.XXXXXX)"
SPECPREFILL_SELECTION_FIXTURE="$(mktemp /tmp/qwen38-specprefill-selection.XXXXXX)"
trap 'rm -f "$ANE_PROFILE" "$VERSION_LOG" "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD" "$MTP_GATE_FIXTURE" "$SPECPREFILL_SELECTION_FIXTURE"' EXIT
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
trap 'rm -f "$ANE_PROFILE" "$VERSION_LOG" "$FAKE_OMLX_OK" "$FAKE_OMLX_BAD" "$MTP_GATE_FIXTURE" "$SPECPREFILL_SELECTION_FIXTURE" "$FALLBACK_LOG" "$FALLBACK_FUNCTION" "$FALLBACK_CALLS"' EXIT
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
