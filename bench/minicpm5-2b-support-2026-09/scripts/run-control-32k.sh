#!/usr/bin/env bash
# Controle da dúvida "o agente paralelo atrapalhou?": re-roda A e B a 32K numa
# janela em que nenhum outro agente/probe está ativo. Espera o run de correção
# (mcp5fix, marcador FIXDONE) terminar antes de começar, para não disputar o
# driver. Cada arranjo reinicia o driver (cold frio de verdade).
#
# Resultados com --tag ctl para não sobrescrever a matriz principal.
# uso: screen -dmS mcp5ctl bash -lc "bash scripts/run-control-32k.sh"
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs/control-32k.log"
FIXLOG="$HERE/logs/etapa2-fix.log"

mkdir -p "$HERE/logs"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] control: aguardando mcp5fix terminar" >>"$LOG"
for _ in $(seq 1 480); do
  grep -q FIXDONE "$FIXLOG" 2>/dev/null && break
  sleep 30
done
# Folga para o driver/suporte do fix liberarem memoria.
sleep 20

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] control begin" >>"$LOG"
for ARM in A B; do
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] control BEGIN $ARM" >>"$LOG"
  bash "$HERE/scripts/run-arrangement.sh" "$ARM" 32768 \
    --repeat 3 --restart-driver --tag ctl >>"$LOG" 2>&1
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] control END $ARM exit=$?" >>"$LOG"
done
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] CONTROLDONE" >>"$LOG"
# Encerra o screen do fix, ja concluido.
screen -S mcp5fix -X quit 2>/dev/null || true