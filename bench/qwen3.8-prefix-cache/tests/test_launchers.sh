#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS="$ROOT/bench/qwen3.8-prefix-cache/scripts"

bash -n "$SCRIPTS/run-mlx-serve.sh"
bash -n "$SCRIPTS/run-llama-cpp.sh"
bash -n "$SCRIPTS/run-campaign.sh"
bash -n "$SCRIPTS/download-models.sh"

MODEL_ROOT="/tmp/qwen38-launcher-fixture"
MLX_A="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-mlx-serve.sh" A --print)"
MLX_B="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-mlx-serve.sh" B --print)"
MLX_C="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-mlx-serve.sh" C --print)"
GGUF_D="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" D --print)"
GGUF_E="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" E --print)"
GGUF_F="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" F --print)"
GGUF_G="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" G --print)"
GGUF_H="$(QWEN38_MODEL_ROOT="$MODEL_ROOT" bash "$SCRIPTS/run-llama-cpp.sh" H --print)"

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

if bash "$SCRIPTS/run-mlx-serve.sh" D --print >/dev/null 2>&1; then
  echo "MLX launcher accepted invalid arm D" >&2
  exit 1
fi

if bash "$SCRIPTS/run-llama-cpp.sh" C --print >/dev/null 2>&1; then
  echo "GGUF launcher accepted invalid arm C" >&2
  exit 1
fi

SMOKE="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" smoke)"
grep -q -- 'arm=A context=8192' <<<"$SMOKE"
grep -q -- 'arm=B context=8192' <<<"$SMOKE"
grep -q -- 'arm=D context=8192' <<<"$SMOKE"
grep -q -- 'arm=E context=8192' <<<"$SMOKE"
! grep -q -- 'arm=C context=8192' <<<"$SMOKE"

MTP="$(QWEN38_DRY_RUN=1 bash "$SCRIPTS/run-campaign.sh" mtp-32k)"
grep -q -- 'arm=C context=32768' <<<"$MTP"
grep -q -- 'arm=F context=32768' <<<"$MTP"

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
