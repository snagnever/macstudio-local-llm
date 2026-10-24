#!/usr/bin/env bash
# Run one arm of the splash-longctx-2026-10 campaign with the 2026-09 driver, writing results/ and
# logs/ here. Same arguments as run-candidate.sh.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
