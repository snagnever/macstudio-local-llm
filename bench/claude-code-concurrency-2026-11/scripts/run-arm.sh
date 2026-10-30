#!/usr/bin/env bash
# Run one arm of the claude-code-concurrency-2026-11 campaign (rc1|rc2|rc2s|rc2d|rm1|rm2|rm2s) with the 2026-09
# driver, writing results/ and logs/ here. Same arguments as run-candidate.sh:
#   run-arm.sh rc2 131072 --tag r1            FLASHNEXT_CC_PAIR=a,b run-arm.sh rc2 131072 --tag r1
#   FLASHNEXT_CC_TASK=c run-arm.sh rc1 131072 --tag r1
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
