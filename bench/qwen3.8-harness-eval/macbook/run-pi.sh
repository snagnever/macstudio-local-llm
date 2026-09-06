#!/usr/bin/env bash
# Pi apontado para o rig (provider RIG_PROVIDER registrado em
# ~/.pi/agent/models.json, um provider por porta). O effort vai em --thinking. Na sessao, /thinking
# troca o nivel e Shift+Tab cicla.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-pi-{27b,fn}.sh [dir-do-run] [--print] [args extra do pi]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

launch pi --model "$RIG_PROVIDER/$RIG_MODEL_ID" --thinking "$EFFORT" "$@"
