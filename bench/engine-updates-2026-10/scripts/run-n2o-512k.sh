#!/usr/bin/env bash
# n2 a 512K (YaRN 2.0 + KV 8-bit) com --os-reserve-gib 4, 1 rep, tag osr. Testa se a folga de 4 GB evita o
# PrefillDoesNotFit que os runs yarn2 e yarn2r tiveram (faltaram 0.6 e 3.2 GB). Disparo manual.
#
# Guarda: sai com 75 sem rodar nada se houver processo de outra campanha que usa a porta 11234 (padrão em
# ENGINE_GUARD_PATTERN, default "swift15"). O run-candidate.sh derruba o que escuta na 11234, então este script
# não pode começar enquanto outra sessão mede. No fim, relança o driver diário só se a porta estiver livre.
# Uso: run-n2o-512k.sh [n2o|n2o2] (default n2o; n2o2 = reserva 2 GB, tag osr2). ENGINE_NO_DRIVER=1 não relança o
# driver (a outra campanha retoma a porta). ENGINE_REPEAT=N roda N reps (tag com sufixo xN). ENGINE_BAND_DRY=1 só imprime.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WT="$(cd "$HERE/../.." && pwd)"
GUARD="${ENGINE_GUARD_PATTERN:-swift15}"
DRY="${ENGINE_BAND_DRY:-}"
ARM="${1:-n2o}"
case "$ARM" in n2o) TAG=osr ;; n2o2) TAG=osr2 ;; *) echo "run-n2o-512k: braço desconhecido: $ARM" >&2; exit 64 ;; esac
REPEAT="${ENGINE_REPEAT:-1}"
[[ "$REPEAT" == 1 ]] || TAG="${TAG}x${REPEAT}"

if pgrep -f "$GUARD" >/dev/null 2>&1; then
  echo "run-n2o-512k: processo ativo casa com '$GUARD'; outra campanha usa a porta 11234. Nada foi rodado." >&2
  exit 75
fi

RUN=(bash "$HERE/scripts/run-arm.sh" "$ARM" 524288 --yarn 2.0 --repeat "$REPEAT" --tag "$TAG")
DRIVER=(bash "$WT/tools/scripts/serve-flashnext-daily-driver.sh" daily)
if [[ -n "$DRY" ]]; then
  echo "run-arm.sh ${RUN[*]:2}"
  [[ -n "${ENGINE_NO_DRIVER:-}" ]] || echo "serve-flashnext-daily-driver.sh ${DRIVER[*]:2}"
  exit 0
fi

echo "=== $(date -u +%H:%M:%S) $ARM 524288 $TAG"
"${RUN[@]}"; echo "=== exit[$ARM@524288]=$? $(date -u +%H:%M:%S)"
sleep 30
if [[ -n "${ENGINE_NO_DRIVER:-}" ]]; then
  for _ in $(seq 60); do lsof -tiTCP:11234 -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 2; done
  lsof -tiTCP:11234 -sTCP:LISTEN >/dev/null 2>&1 && echo "=== AINDA OUVINDO na 11234" \
    || echo "=== porta 11234 livre $(date -u +%H:%M:%S); driver não relançado (ENGINE_NO_DRIVER)"
  exit 0
fi
if pgrep -f "$GUARD" >/dev/null 2>&1 || lsof -tiTCP:11234 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "=== porta 11234 ocupada ou outra campanha ativa: driver diário não relançado"
  exit 0
fi
cd "$WT" && nohup "${DRIVER[@]}" > "${TMPDIR:-/tmp}/flashnext-daily-driver.log" 2>&1 < /dev/null &
disown
echo "=== $(date -u +%H:%M:%S) driver diário relançado"
