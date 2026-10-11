#!/usr/bin/env bash
# Fila completa da campanha, para rodar desacoplada (nohup): bateria n2, bateria w1 (t1 e t0) e T_turno
# (n2 e w1 a 32K, depois w1 e n2 a 128K). Cada passo grava o próprio código de saída; um passo que falha
# não para a fila. ALL_DRY=1 só imprime os comandos.
# ALL_STEPS troca a fila (para retomar depois de uma pausa). Formas de passo:
#   ab-<braço>                      bateria completa (t1 e t0)
#   ab-<braço>-<perfil>[:s1,s2,..]  um perfil; com ':' só as suítes listadas
#   fn-<braço>-<ctx>                T_turno, 3 reps
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs"; mkdir -p "$LOG"
STEPS="${ALL_STEPS:-ab-n2 ab-w1 fn-n2-32768 fn-w1-32768 fn-w1-131072 fn-n2-131072}"

# Valida a fila inteira antes de rodar o primeiro passo: um nome errado no fim não pode aparecer só horas depois.
for step in $STEPS; do
  [[ "$step" =~ ^ab-(n2|w1)(-(t0|t1)(:[a-z,]+)?)?$ || "$step" =~ ^fn-(n2|w1)-[0-9]+$ ]] \
    || { echo "run-all: passo desconhecido: $step" >&2; exit 64; }
done

run() {
  local name="$1"; shift
  if [[ -n "${ALL_DRY:-}" ]]; then echo "$name: $*"; return 0; fi
  echo "=== $(date '+%F %T') start $name"
  "$@" >"$LOG/$name.log" 2>&1; local rc=$?
  echo "=== $(date '+%F %T') done $name rc=$rc"
  sleep 120
}

for step in $STEPS; do
  name="${step%%:*}"
  IFS=- read -r kind arm third <<<"$name"
  case "$kind" in
    ab)
      if [[ -z "$third" ]]; then
        run "$name" caffeinate -i bash "$HERE/scripts/run-ab.sh" "$arm"
      elif [[ "$step" == *:* ]]; then
        suites="${step#*:}"; suites="${suites//,/ }"
        if [[ -n "${ALL_DRY:-}" ]]; then
          echo "$name: AB_SUITES='$suites' caffeinate -i bash $HERE/scripts/run-ab.sh $arm --profiles $third"
        else
          ( export AB_SUITES="$suites"; run "$name" caffeinate -i bash "$HERE/scripts/run-ab.sh" "$arm" --profiles "$third" )
        fi
      else
        run "$name" caffeinate -i bash "$HERE/scripts/run-ab.sh" "$arm" --profiles "$third"
      fi ;;
    fn) run "$name" caffeinate -i bash "$HERE/scripts/run-arm.sh" "$arm" "$third" --repeat 3 --tag fn ;;
  esac
done
[[ -n "${ALL_DRY:-}" ]] || echo "=== $(date '+%F %T') fila completa"
