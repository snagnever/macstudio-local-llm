#!/usr/bin/env bash
# Qwen Code apontado para o rig (OpenAI /v1/chat/completions via Tailscale).
# O effort vai no settings de workspace do diretorio do run
# (<dir>/.qwen/settings.json), que sobrepoe o ~/.qwen/settings.json do usuario.
# Duas chaves: model.reasoningEffort (o Qwen Code envia como reasoning.effort,
# formato Responses) e generationConfig.extra_body.reasoning_effort (campo que
# o mlx-dspark e o mlx-serve honram). Na sessao, /effort troca so a primeira.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-qc-{27b,fn}.sh [dir-do-run] [--print] [args extra do qwen]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

export_env OPENAI_BASE_URL "http://$RIG_HOST:$RIG_PORT/v1"
export_env OPENAI_API_KEY "local"
export_env OPENAI_MODEL "$RIG_MODEL_ID"

mkdir -p "$DIR/.qwen"
cat >"$DIR/.qwen/settings.json" <<EOF
{
  "model": {
    "reasoningEffort": "$EFFORT",
    "generationConfig": {
      "extra_body": { "reasoning_effort": "$EFFORT" }
    }
  }
}
EOF
ENV_LINES+=("QWEN_WORKSPACE_SETTINGS=$DIR/.qwen/settings.json")

launch qwen -m "$RIG_MODEL_ID" "$@"
