#!/usr/bin/env bash
# Fila completa da campanha, para rodar desacoplada (nohup): bateria n2, bateria w1 (t1 e t0) e T_turno
# (n2 e w1 a 32K, depois w1 e n2 a 128K). Cada passo grava o próprio código de saída; um passo que falha
# não para a fila. ALL_DRY=1 só imprime os comandos.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs"; mkdir -p "$LOG"
run() {
  local name="$1"; shift
  if [[ -n "${ALL_DRY:-}" ]]; then echo "$name: $*"; return 0; fi
  echo "=== $(date '+%F %T') start $name"
  "$@" >"$LOG/$name.log" 2>&1; local rc=$?
  echo "=== $(date '+%F %T') done $name rc=$rc"
  sleep 120
}
run ab-n2 caffeinate -i bash "$HERE/scripts/run-ab.sh" n2
run ab-w1 caffeinate -i bash "$HERE/scripts/run-ab.sh" w1
for spec in "n2 32768" "w1 32768" "w1 131072" "n2 131072"; do
  set -- $spec
  run "fn-$1-$2" caffeinate -i bash "$HERE/scripts/run-arm.sh" "$1" "$2" --repeat 3 --tag fn
done
echo "=== $(date '+%F %T') fila completa"
