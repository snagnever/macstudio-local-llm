#!/usr/bin/env bash
# Claude Code apontado para o 27B no rig (oMLX, Anthropic /v1/messages via Tailscale).
# Nao toca em ~/.claude/settings.json; as variaveis valem so nesta shell.
# Uso: bench/qwen3.8-harness-eval/macbook/run-cc-27b.sh [dir-do-run] [args extra do claude]
set -euo pipefail
DIR="${1:-.}"; shift || true
export ANTHROPIC_BASE_URL="http://mac-studio:8484"
export ANTHROPIC_AUTH_TOKEN="local"
export ANTHROPIC_MODEL="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
export ANTHROPIC_DEFAULT_SONNET_MODEL="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
export ANTHROPIC_DEFAULT_OPUS_MODEL="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
export CLAUDE_CODE_SUBAGENT_MODEL="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="131072"
cd "$DIR"
exec claude "$@"
