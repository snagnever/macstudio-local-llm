#!/usr/bin/env bash
# Claude Code apontado para o rig (Anthropic /v1/messages via Tailscale).
# Nao toca em ~/.claude/settings.json; as variaveis valem so nesta shell.
# O effort vai em CLAUDE_CODE_EFFORT_LEVEL, que tem precedencia sobre /effort e
# settings.json e nao persiste. Nao use /effort na sessao: ele grava no
# settings.json do usuario.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-cc-{27b,fn}.sh [dir-do-run] [--print] [args extra do claude]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

export_env ANTHROPIC_BASE_URL "http://$RIG_HOST:$RIG_PORT"
export_env ANTHROPIC_AUTH_TOKEN "local"
export_env ANTHROPIC_MODEL "$RIG_MODEL_ID"
export_env ANTHROPIC_DEFAULT_HAIKU_MODEL "$RIG_MODEL_ID"
export_env ANTHROPIC_DEFAULT_SONNET_MODEL "$RIG_MODEL_ID"
export_env ANTHROPIC_DEFAULT_OPUS_MODEL "$RIG_MODEL_ID"
export_env CLAUDE_CODE_SUBAGENT_MODEL "$RIG_MODEL_ID"
export_env CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC "1"
export_env CLAUDE_CODE_MAX_CONTEXT_TOKENS "131072"
export_env CLAUDE_CODE_EFFORT_LEVEL "$EFFORT"

launch claude "$@"
