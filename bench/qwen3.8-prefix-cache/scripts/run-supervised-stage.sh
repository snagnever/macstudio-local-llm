#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RUN_CAMPAIGN="$ROOT/bench/qwen3.8-prefix-cache/scripts/run-campaign.sh"
STAGE="${1:?stage is required}"
LOG_PATH="${2:?log path is required}"
EXIT_PATH="${3:?exit marker path is required}"

mkdir -p "$(dirname "$LOG_PATH")" "$(dirname "$EXIT_PATH")"
set +e
bash "$RUN_CAMPAIGN" "$STAGE" >>"$LOG_PATH" 2>&1
RC=$?
set -e

TEMP_EXIT="${EXIT_PATH}.tmp.$$"
printf '%s\n' "$RC" >"$TEMP_EXIT"
mv "$TEMP_EXIT" "$EXIT_PATH"
exit "$RC"
