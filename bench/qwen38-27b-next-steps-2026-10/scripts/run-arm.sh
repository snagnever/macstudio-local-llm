#!/usr/bin/env bash
# Runs one arm through the 2026-09 driver with results and logs inside this campaign.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
