#!/usr/bin/env bash
# Shared by the macbook/run-*.sh launchers. Source it; do not run it.
#
# Inputs (env):
#   TARGET        model served by the rig: 27b | fn (default 27b)
#   EFFORT        reasoning effort of the run (default medium). Values:
#                 none | minimal | low | medium | high | xhigh
#   RIG_HOST      rig hostname on the tailnet (default mac-studio)
#   RIG_PORT      runtime port on the rig (default from TARGET)
#   RIG_MODEL_ID  model-id served by the runtime (default from TARGET;
#                 confirm with /v1/models)
#   RIG_PROVIDER  provider entry in the harness config (default from TARGET)
#
# Positional: [run-dir] [--print] [extra harness args]
#   --print echoes the env lines and the command instead of executing.
#
# The runtime does NOT validate the effort string: mlx-serve accepted an
# invalid value and answered with the model default (probe of 2026-09-05).
# The validation below is the only guard against a typo silently becoming a
# default-effort run.

TARGET="${TARGET:-27b}"
case "$TARGET" in
  27b)
    # mlx-dspark arm S, 8-bit + DFlash2 drafter.
    DEFAULT_PORT=8484
    DEFAULT_MODEL_ID="mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
    DEFAULT_PROVIDER="rig"
    ;;
  fn)
    # mlx-serve arm FS, build ddalcu mixed-4/8 (Flash-Next).
    DEFAULT_PORT=11234
    DEFAULT_MODEL_ID="ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
    DEFAULT_PROVIDER="rigfn"
    ;;
  *)
    echo "TARGET must be 27b or fn (got '$TARGET')" >&2
    exit 64
    ;;
esac

RIG_HOST="${RIG_HOST:-mac-studio}"
RIG_PORT="${RIG_PORT:-$DEFAULT_PORT}"
RIG_MODEL_ID="${RIG_MODEL_ID:-$DEFAULT_MODEL_ID}"
RIG_PROVIDER="${RIG_PROVIDER:-$DEFAULT_PROVIDER}"
EFFORT="${EFFORT:-medium}"

case "$EFFORT" in
  none|minimal|low|medium|high|xhigh) ;;
  *)
    echo "EFFORT must be none, minimal, low, medium, high or xhigh (got '$EFFORT')" >&2
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
