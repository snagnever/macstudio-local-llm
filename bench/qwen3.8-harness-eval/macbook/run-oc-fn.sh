#!/usr/bin/env bash
# OpenCode no alvo fn (Flash-Next, mlx-serve arm FS, build ddalcu mixed-4/8, porta 11234).
# Wrapper de TARGET; a implementacao esta em run-oc.sh.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-oc-fn.sh [dir-do-run] [--print] [args extra]
set -euo pipefail
export TARGET=fn
exec "$(dirname "${BASH_SOURCE[0]}")/run-oc.sh" "$@"
