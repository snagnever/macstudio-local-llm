#!/usr/bin/env bash
# Shared by the macbook/run-*-27b.sh launchers. Source it; do not run it.
#
# Inputs (env):
#   EFFORT        reasoning effort of the run: low | medium | xhigh (default medium)
#   RIG_HOST      rig hostname on the tailnet (default mac-studio)
#   RIG_PORT      runtime port on the rig (default 8484, mlx-dspark arm S)
#   RIG_MODEL_ID  model-id served by the runtime (confirm with /v1/models)
#
# Positional: [run-dir] [--print] [extra harness args]
#   --print echoes the env lines and the command instead of executing.

RIG_HOST="${RIG_HOST:-mac-studio}"
RIG_PORT="${RIG_PORT:-8484}"
RIG_MODEL_ID="${RIG_MODEL_ID:-mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9}"
EFFORT="${EFFORT:-medium}"

case "$EFFORT" in
  low|medium|xhigh) ;;
  *)
    echo "EFFORT must be low, medium or xhigh (got '$EFFORT')" >&2
    exit 64
    ;;
esac

PRINT=0
if [[ "${1:-}" == "--print" ]]; then
  DIR="."
  PRINT=1
  shift
else
  DIR="${1:-.}"
  shift || true
  if [[ "${1:-}" == "--print" ]]; then
    PRINT=1
    shift
  fi
fi

# Env lines to echo in --print mode. Launchers append "KEY=VALUE" strings.
ENV_LINES=()

# export_env KEY VALUE: export the variable and record it for --print.
export_env() {
  export "$1=$2"
  ENV_LINES+=("$1=$2")
}

# launch CMD ARGS...: exec the harness, or print env lines + command.
launch() {
  if [[ "$PRINT" -eq 1 ]]; then
    if [[ "${#ENV_LINES[@]}" -gt 0 ]]; then
      printf '%s\n' "${ENV_LINES[@]}"
    fi
    printf '%s\n' "$*"
    exit 0
  fi
  cd "$DIR"
  exec "$@"
}
