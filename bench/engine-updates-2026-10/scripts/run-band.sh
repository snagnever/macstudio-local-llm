#!/usr/bin/env bash
# Uma banda (32K ou 128K) de uma parte (fn = Flash-Next, 27b), 3 reps. A ordem a 128K é a
# inversa da de 32K. O d1 só entra com ENGINE_D1=1 (passou o gate do smoke).
# ENGINE_BAND_DRY=1 só imprime os comandos.
set -euo pipefail
PART="${1:?uso: $0 <fn|27b> <32768|131072>}"; CTX="${2:?ctx}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "$PART" in
  fn) ARMS=(n2 m1 o1); [[ -n "${ENGINE_D1:-}" ]] && ARMS+=(d1); TAG=fn ;;
  27b) ARMS=(r27 m27 o27 s27); TAG=d27 ;;
  *) echo "parte fora do plano: $PART" >&2; exit 64 ;;
esac
case "$CTX" in
  32768) ORDER=("${ARMS[@]}") ;;
  131072) ORDER=(); for ((i=${#ARMS[@]}-1; i>=0; i--)); do ORDER+=("${ARMS[$i]}"); done ;;
  *) echo "banda fora do plano: $CTX" >&2; exit 64 ;;
esac
for arm in "${ORDER[@]}"; do
  if [[ -n "${ENGINE_BAND_DRY:-}" ]]; then
    echo "bash run-arm.sh $arm $CTX --repeat 3 --tag $TAG"; continue
  fi
  rc=0; bash "$HERE/scripts/run-arm.sh" "$arm" "$CTX" --repeat 3 --tag "$TAG" || rc=$?
  echo "exit[$arm@$CTX]=$rc"
  sleep 120
done
