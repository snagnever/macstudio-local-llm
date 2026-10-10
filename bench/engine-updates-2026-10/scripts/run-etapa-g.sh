#!/usr/bin/env bash
# Etapa G: dados que faltam para a página perf-lines. Fila única, um servidor por vez, tag pg.
#   G1: n2, o1, m1, d1 a 8K (3 reps).
#   G2: MTPLX ao máximo a 128K (3 reps): m1v (config do vendor); se recusar (HTTP 4xx/5xx no cold),
#       m1x (--memory-limit max); se recusar, m1q (KV q8). O primeiro que passa ganha 256K (1 rep).
#   G3: d1 a 128K (3 reps), 256K (1 rep) e 512K com YaRN 2 (1 rep).
# No fim relança o driver diário.
# ENGINE_G_PARTS="g1 g2 g3" escolhe os blocos; ENGINE_G2_ARMS="m1v m1x m1q" a ordem do ramo da G2.
# ENGINE_BAND_DRY=1 só imprime a fila; no dry run, ENGINE_G_REFUSED=m1v,m1x simula recusas.
# `source run-etapa-g.sh --lib` só define as funções (testes); nunca roda a fila.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DRY="${ENGINE_BAND_DRY:-}"
RESULTS="${RESULTS:-$HERE/results}"

run() {  # run <arm> <ctx> <reps> [args...]
  local arm="$1" ctx="$2" reps="$3"; shift 3
  if [[ -n "$DRY" ]]; then echo "bash run-arm.sh $arm $ctx --repeat $reps $* --tag pg"; return 0; fi
  echo "=== $(date -u +%H:%M:%S) $arm $ctx x$reps $*"
  local rc=0; bash "$HERE/scripts/run-arm.sh" "$arm" "$ctx" --repeat "$reps" "$@" --tag pg || rc=$?
  echo "=== exit[$arm@$ctx]=$rc $(date -u +%H:%M:%S)"
  sleep 120
}

refused() {  # refused <arm> <ctx>: o cold tem erro HTTP (507 do memory plan, 400 da janela de contexto)
  if [[ -n "$DRY" ]]; then [[ ",${ENGINE_G_REFUSED:-}," == *",$1,"* ]]; return; fi
  grep '"scenario": "cold"' "$RESULTS/$1-$2-t1.0-pg.jsonl" 2>/dev/null | grep -q '"error": "http_'
}

if [[ "${1:-}" == --lib ]]; then return 0 2>/dev/null || exit 0; fi

PARTS=" ${ENGINE_G_PARTS:-g1 g2 g3} "
if [[ "$PARTS" == *" g1 "* ]]; then
  for arm in n2 o1 m1 d1; do run "$arm" 8192 3; done
fi
if [[ "$PARTS" == *" g2 "* ]]; then
  for arm in ${ENGINE_G2_ARMS:-m1v m1x m1q}; do
    run "$arm" 131072 3
    if ! refused "$arm" 131072; then run "$arm" 262144 1; break; fi
  done
fi
if [[ "$PARTS" == *" g3 "* ]]; then
  run d1 131072 3
  run d1 262144 1
  run d1 524288 1 --yarn 2.0
fi

if [[ -n "$DRY" ]]; then echo "relaunch daily driver"; exit 0; fi
sleep 30
cd "$REPO" && nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > "${ENGINE_G_DRIVER_LOG:-/tmp/flashnext-daily-driver.log}" 2>&1 &
echo "=== SEQ DONE driver diário relançado $(date -u +%H:%M:%S)"
