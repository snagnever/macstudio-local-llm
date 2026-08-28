#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CACHE_BASE="${XDG_CACHE_HOME:-${HOME}/.cache}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-$CACHE_BASE/local-llms/qwen3.8-prefix-cache}"
OUTPUT="${QWEN38_ARTIFACT_MANIFEST:-$ROOT/bench/qwen3.8-prefix-cache/results/artifacts.json}"

MODEL_ARGS=(
  --model ddalcu/Qwen3.8-27B-MLX-Serve-8bit 011e38296b3d2aa99245ed49a700459c4ac246b6 "$MODEL_ROOT/ddalcu-Qwen3.8-27B-MLX-Serve-8bit-011e38296b3d2aa99245ed49a700459c4ac246b6"
  --model unsloth/Qwen3.8-27B-GGUF 4ca720788d1e01f1bff70c033e0d0028fd02e502 "$MODEL_ROOT/unsloth-Qwen3.8-27B-GGUF-4ca720788d1e01f1bff70c033e0d0028fd02e502"
  --model True2456/Qwen3.8-27B-AWQ-5.0bpw dc699a76ddcbef44c188a8aee2ccc79ccc339a04 "$MODEL_ROOT/True2456-Qwen3.8-27B-AWQ-5.0bpw-dc699a76ddcbef44c188a8aee2ccc79ccc339a04"
  --model mlx-community/Qwen3.8-27B-8bit 815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9 "$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
  --model RadixArk/Qwen3.8-27B-DSpark 85ef153be924f17ce4bf62726954eeaa4a73e854 "$MODEL_ROOT/RadixArk--Qwen3.8-27B-DSpark-85ef153be924f17ce4bf62726954eeaa4a73e854"
  --model incoai/Qwen3.8-27B-DFlash2 dedf8df68adfb1afeaf7b7480c0a0243108177b4 "$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4"
  --model Jundot/Qwen3.8-27B-oQ8e-mtp c99e5aad8a478f71c10b9a3dde6709158b690da6 "$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-mtp-c99e5aad8a478f71c10b9a3dde6709158b690da6"
  --model Jundot/Qwen3.8-27B-oQ8e-fp16-mtp 4761782b9455f335292f4d6cb0c89570dff27a11 "$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-fp16-mtp-4761782b9455f335292f4d6cb0c89570dff27a11"
  --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed 123db8bcc7101455b00d9aad36c0e760c6e7de02 "$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-123db8bcc7101455b00d9aad36c0e760c6e7de02"
  --model gcoli/Qwen3.8-27B-oQ4e-mtp c41ed507f1b16320942a1e9ce340e71d2692dee2 "$MODEL_ROOT/gcoli-Qwen3.8-27B-oQ4e-mtp-c41ed507f1b16320942a1e9ce340e71d2692dee2"
  --model Qwen/Qwen3.5-2B 15852e8c16360a2fea060d615a32b45270f8a8fc "$MODEL_ROOT/Qwen-Qwen3.5-2B-15852e8c16360a2fea060d615a32b45270f8a8fc"
  --model Qwen/Qwen3.5-0.8B 2fc06364715b967f1860aea9cf38778875588b17 "$MODEL_ROOT/Qwen-Qwen3.5-0.8B-2fc06364715b967f1860aea9cf38778875588b17"
)

python3 "$ROOT/bench/qwen3.8-prefix-cache/scripts/artifact_manifest.py" \
  --output "$OUTPUT" \
  "${MODEL_ARGS[@]}"
