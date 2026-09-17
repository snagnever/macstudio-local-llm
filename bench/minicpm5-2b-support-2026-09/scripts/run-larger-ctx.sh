#!/usr/bin/env bash
# Verifica se o s1 cabe com contexto maior (256K/512K), usando o perfil 512k do
# driver (524288 com YaRN 2.0 + KV 8-bit). Mede A e B em 256K e 512K, 1 rep,
# para separar "cabe?" (memoria/contexto) de "quanto custa" (T_turno).
#
# uso: screen -dmS mcp5big bash -lc "bash scripts/run-larger-ctx.sh"
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$HERE/logs/larger-ctx.log"
mkdir -p "$HERE/logs"
export DRIVER_PROFILE=512k

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] larger-ctx begin (perfil $DRIVER_PROFILE)" >>"$LOG"
for spec in "A 262144" "B 262144" "A 524288" "B 524288"; do
  set -- $spec
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] larger-ctx BEGIN arm=$1 ctx=$2" >>"$LOG"
  bash "$HERE/scripts/run-arrangement.sh" "$1" "$2" --repeat 1 --restart-driver >>"$LOG" 2>&1
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] larger-ctx END arm=$1 ctx=$2 exit=$?" >>"$LOG"
done
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] LARGERDONE" >>"$LOG"