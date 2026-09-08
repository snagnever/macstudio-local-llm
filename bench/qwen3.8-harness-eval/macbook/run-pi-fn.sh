#!/usr/bin/env bash
# Pi no alvo fn (Flash-Next, mlx-serve arm FS, build ddalcu mixed-4/8, porta 11234).
# Wrapper de TARGET; a implementacao esta em run-pi.sh.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-pi-fn.sh [dir-do-run] [--print] [args extra]
set -euo pipefail
export TARGET=fn
exec "$(dirname "${BASH_SOURCE[0]}")/run-pi.sh" "$@"
