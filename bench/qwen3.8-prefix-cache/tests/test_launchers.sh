#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPTS="$ROOT/bench/qwen3.8-prefix-cache/scripts"

bash -n "$SCRIPTS/run-mlx-serve.sh"
bash -n "$SCRIPTS/run-llama-cpp.sh"
bash -n "$SCRIPTS/run-campaign.sh"

MLX_A="$(bash "$SCRIPTS/run-mlx-serve.sh" A --print)"
MLX_B="$(bash "$SCRIPTS/run-mlx-serve.sh" B --print)"
MLX_C="$(bash "$SCRIPTS/run-mlx-serve.sh" C --print)"
GGUF_D="$(bash "$SCRIPTS/run-llama-cpp.sh" D --print)"
GGUF_E="$(bash "$SCRIPTS/run-llama-cpp.sh" E --print)"
GGUF_F="$(bash "$SCRIPTS/run-llama-cpp.sh" F --print)"
GGUF_G="$(bash "$SCRIPTS/run-llama-cpp.sh" G --print)"
GGUF_H="$(bash "$SCRIPTS/run-llama-cpp.sh" H --print)"

grep -q -- 'ddalcu/Qwen3.8-27B-MLX-Serve-8bit' <<<"$MLX_C"
grep -q -- '--prefix-cache-entries 0' <<<"$MLX_A"
grep -q -- '--no-mtp' <<<"$MLX_A"
grep -q -- '--no-pld' <<<"$MLX_A"
grep -q -- '--no-mtp' <<<"$MLX_B"
grep -q -- '--no-pld' <<<"$MLX_B"
! grep -q -- '--no-mtp' <<<"$MLX_C"
! grep -q -- '--no-pld' <<<"$MLX_C"
! grep -q -- '--mtp-depth' <<<"$MLX_C"

grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_D"
grep -q -- '--no-cache-prompt' <<<"$GGUF_D"
grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_E"
! grep -q -- '--spec-type' <<<"$GGUF_E"
grep -q -- 'UD-Q4_K_XL' <<<"$GGUF_F"
grep -q -- '--spec-type draft-mtp' <<<"$GGUF_F"
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
