#!/usr/bin/env bash
# OpenCode no alvo 27b (mlx-dspark arm S, 8-bit + DFlash2, porta 8484).
# Wrapper de TARGET; a implementacao esta em run-oc.sh.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-oc-27b.sh [dir-do-run] [--print] [args extra]
set -euo pipefail
export TARGET=27b
exec "$(dirname "${BASH_SOURCE[0]}")/run-oc.sh" "$@"
