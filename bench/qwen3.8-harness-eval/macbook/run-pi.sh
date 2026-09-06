#!/usr/bin/env bash
# Pi apontado para o 27B no rig (provider 'rig' registrado em
# ~/.pi/agent/models.json). O effort vai em --thinking. Na sessao, /thinking
# troca o nivel e Shift+Tab cicla.
# Uso: EFFORT=<low|medium|xhigh> bench/qwen3.8-harness-eval/macbook/run-pi-27b.sh [dir-do-run] [--print] [args extra do pi]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

launch pi --model "rig/$RIG_MODEL_ID" --thinking "$EFFORT" "$@"
