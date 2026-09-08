#!/usr/bin/env bash
# Claude Code no alvo 27b (mlx-dspark arm S, 8-bit + DFlash2, porta 8484).
# Wrapper de TARGET; a implementacao esta em run-cc.sh.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-cc-27b.sh [dir-do-run] [--print] [args extra]
set -euo pipefail
export TARGET=27b
exec "$(dirname "${BASH_SOURCE[0]}")/run-cc.sh" "$@"
