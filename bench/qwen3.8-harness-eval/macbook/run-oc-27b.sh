#!/usr/bin/env bash
# OpenCode apontado para o 27B no rig (provider 'rig' registrado em
# ~/.config/opencode/opencode.jsonc, com variants low/medium/xhigh no modelo).
# O TUI nao tem --variant; a variante default dos agentes build e plan e o
# baseURL do provider entram por OPENCODE_CONFIG_CONTENT (merge sobre a config
# global). Na sessao, ctrl+t cicla a variante.
# Uso: EFFORT=<low|medium|xhigh> bench/qwen3.8-harness-eval/macbook/run-oc-27b.sh [dir-do-run] [--print] [args extra]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

OC_MODEL="rig/$RIG_MODEL_ID"
export_env OPENCODE_CONFIG_CONTENT "$(printf '{"model":"%s","provider":{"rig":{"options":{"baseURL":"http://%s:%s/v1"}}},"agent":{"build":{"model":"%s","variant":"%s"},"plan":{"model":"%s","variant":"%s"}}}' \
  "$OC_MODEL" "$RIG_HOST" "$RIG_PORT" "$OC_MODEL" "$EFFORT" "$OC_MODEL" "$EFFORT")"

# "$@" antes de --model para que `run <prompt>` funcione como subcomando.
launch opencode "$@" --model "$OC_MODEL"
