#!/usr/bin/env bash
# OpenCode apontado para o 27B no rig (provider 'rig' ja registrado no ~/.config/opencode).
# Uso: bench/qwen3.8-harness-eval/macbook/run-oc-27b.sh [dir-do-run] [args extra]
set -euo pipefail
DIR="${1:-.}"; shift || true
cd "$DIR"
exec opencode --model "rig/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9" "$@"
