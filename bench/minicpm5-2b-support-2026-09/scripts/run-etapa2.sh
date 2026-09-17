#!/usr/bin/env bash
# Supervisor da Etapa 2: roda a matriz arranjo x banda, reiniciando o driver
# antes de cada arranjo para que o `cold` de cada um seja realmente frio (o
# prefix-cache em disco do mlx-serve persistiria entre arranjos da mesma banda).
#
# Ordem: banda externa, arranjo interno — todos os arranjos a 32K, depois todos
# a 128K, como no plano. Cada arranjo custa um restart de driver (~4 min) mais
# o probe.
#
# uso: nohup bash run-etapa2.sh > logs/etapa2-supervisor.log 2>&1 &
# env: BANDS="32768 131072"  ARMS="A B C D"  REPEAT=3  LOAD_DUR=7200
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BANDS="${BANDS:-32768 131072}"
ARMS="${ARMS:-A B C D}"
REPEAT="${REPEAT:-3}"
LOAD_DUR="${LOAD_DUR:-7200}"
LOG="$HERE/logs/etapa2-campaign.log"

mkdir -p "$HERE/logs" "$HERE/results"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] etapa2 start bands=[$BANDS] arms=[$ARMS] repeat=$REPEAT" | tee -a "$LOG"

for CTX in $BANDS; do
  for ARM in $ARMS; do
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] BEGIN arm=$ARM ctx=$CTX" | tee -a "$LOG"
    bash "$HERE/scripts/run-arrangement.sh" "$ARM" "$CTX" \
      --repeat "$REPEAT" --load-duration "$LOAD_DUR" --restart-driver \
      >>"$LOG" 2>&1
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] END arm=$ARM ctx=$CTX exit=$?" | tee -a "$LOG"
  done
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] etapa2 done" | tee -a "$LOG"