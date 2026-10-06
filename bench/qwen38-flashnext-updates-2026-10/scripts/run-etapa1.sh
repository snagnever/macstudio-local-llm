#!/usr/bin/env bash
# Etapa 1: c1, n1 e n2 numa banda, 3 reps (plan.md, "Protocolo"). A ordem a 128K é a
# inversa da de 32K, para diluir deriva térmica e de page cache. ETAPA1_DRY=1 só imprime.
set -euo pipefail
CTX="${1:?uso: $0 <32768|131072>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "$CTX" in
  32768) ORDER=(c1 n1 n2) ;;
  131072) ORDER=(n2 n1 c1) ;;
  *) echo "banda fora do plano: $CTX" >&2; exit 64 ;;
esac
for arm in "${ORDER[@]}"; do
  cmd=(bash "$HERE/scripts/run-arm.sh" "$arm" "$CTX" --repeat 3 --tag ab)
  if [[ -n "${ETAPA1_DRY:-}" ]]; then
    echo "bash run-arm.sh $arm $CTX --repeat 3 --tag ab"; continue
  fi
  rc=0; "${cmd[@]}" || rc=$?
  [[ "$rc" -eq 0 ]] || echo ">>> $arm@$CTX saiu com $rc; ver results/ e logs/" >&2
done
