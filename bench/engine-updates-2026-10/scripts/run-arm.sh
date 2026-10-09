#!/usr/bin/env bash
# Roda um braço da campanha engine-updates-2026-10 com o driver de 2026-09, gravando
# results/ e logs/ aqui. Mesmos argumentos do run-candidate.sh.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FLASHNEXT_RESULTS_DIR="$HERE/results" FLASHNEXT_LOGS_DIR="$HERE/logs"
exec bash "$HERE/../qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh" "$@"
