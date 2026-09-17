#!/usr/bin/env bash
# Follow-up focado no s1 (MiniCPM5-2B-OptiQ-4bit):
#   1. B @128K limpo (o anterior morreu com o driver caindo)
#   2. Varredura de duty cycle: B @32K com gaps 1/3/5 s entre turnos do suporte,
#      para achar a cadencia em que a perda de T_turno cai abaixo de 15%.
#
# Espera o controle (mcp5ctl, marcador CONTROLDONE) terminar antes de comecar,
# para nao disputar o driver. Roda em background dentro de um screen.
#
# uso: screen -dmS mcp5s1 bash -lc "bash scripts/run-s1-followup.sh"
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs/s1-followup.log"
CTLLOG="$HERE/logs/control-32k.log"
REPEAT="${REPEAT:-2}"
GAPS="${GAPS:-1 3 5}"

mkdir -p "$HERE/logs"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] s1-followup: aguardando CONTROLDONE" >>"$LOG"
for _ in $(seq 1 480); do
  grep -q CONTROLDONE "$CTLLOG" 2>/dev/null && break
  sleep 30
done
sleep 20

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] s1-followup: B@128K limpo" >>"$LOG"
bash "$HERE/scripts/run-arrangement.sh" B 131072 \
  --repeat 3 --restart-driver >>"$LOG" 2>&1
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] s1-followup: B@128K exit=$?" >>"$LOG"

for G in $GAPS; do
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] s1-followup: B@32K gap=${G}s" >>"$LOG"
  bash "$HERE/scripts/run-arrangement.sh" B 32768 \
    --repeat "$REPEAT" --restart-driver --load-gap "$G" >>"$LOG" 2>&1
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] s1-followup: gap=$G exit=$?" >>"$LOG"
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] S1DONE" >>"$LOG"
screen -S mcp5ctl -X quit 2>/dev/null || true