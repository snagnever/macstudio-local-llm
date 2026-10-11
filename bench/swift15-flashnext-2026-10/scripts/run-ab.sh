#!/usr/bin/env bash
# A/B de qualidade com reasoning explícito: sobe o braço (131072) pelo run-candidate.sh uma vez e roda
# ab-battery.sh contra ele, um perfil de sampling após o outro (default "t1 t0").
# --smoke roda só as questões 1-3 do HumanEval e o samplecheck (gate de reasoning e de sampling).
# uso: run-ab.sh <n2|w1> [--profiles "t1 t0"] [--smoke] [--print]
set -euo pipefail
ARM="${1:?uso: $0 <n2|w1> [--profiles \"t1 t0\"] [--smoke] [--print]}"; shift
SMOKE=""; PRINT=(); PROFILES="t1 t0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke) SMOKE=1; shift ;;
    --print) PRINT=(--print); shift ;;
    --profiles) PROFILES="$2"; shift 2 ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done
case "$ARM" in n2|w1) ;; *) echo "braço fora do A/B: $ARM" >&2; exit 64 ;; esac
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AB_ARM="$ARM" AB_PROFILES="$PROFILES"
TAG=ab
if [[ -n "$SMOKE" ]]; then export AB_SUITES="humaneval samplecheck" AB_ONLY=1,2,3 AB_OUT_SUBDIR=ab-smoke; TAG=ab-smoke; fi
# bash 3.2 (o do rig): um array vazio com set -u precisa da forma ${arr[@]+...}.
exec bash "$HERE/scripts/run-arm.sh" "$ARM" 131072 --tag "$TAG" --exec "bash $HERE/scripts/ab-battery.sh" \
  ${PRINT[@]+"${PRINT[@]}"}
