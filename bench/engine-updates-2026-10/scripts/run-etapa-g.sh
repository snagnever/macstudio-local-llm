#!/usr/bin/env bash
# Etapa G: dados que faltam para a página perf-lines. Fila única, um servidor por vez, tag pg.
#   G1: n2, o1, m1, d1 a 8K (3 reps).
#   G2: MTPLX ao máximo a 128K (3 reps): m1v (config do vendor); se recusar (HTTP 507), m1x
#       (--memory-limit max); se recusar, m1q (KV q8). O primeiro que passa ganha 256K (1 rep).
#   G3: d1 a 128K (3 reps), 256K (1 rep) e 512K com YaRN 2 (1 rep).
# No fim relança o driver diário. ENGINE_BAND_DRY=1 só imprime a fila; no dry run,
# ENGINE_G_REFUSED=m1v,m1x simula recusas para testar o ramo da G2.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DRY="${ENGINE_BAND_DRY:-}"

run() {  # run <arm> <ctx> <reps> [args...]
  local arm="$1" ctx="$2" reps="$3"; shift 3
  if [[ -n "$DRY" ]]; then echo "bash run-arm.sh $arm $ctx --repeat $reps $* --tag pg"; return 0; fi
  echo "=== $(date -u +%H:%M:%S) $arm $ctx x$reps $*"
  local rc=0; bash "$HERE/scripts/run-arm.sh" "$arm" "$ctx" --repeat "$reps" "$@" --tag pg || rc=$?
  echo "=== exit[$arm@$ctx]=$rc $(date -u +%H:%M:%S)"
  sleep 120
}

refused() {  # refused <arm> <ctx>: a saída tem HTTP 507 (o MTPLX recusou a janela)
  if [[ -n "$DRY" ]]; then [[ ",${ENGINE_G_REFUSED:-}," == *",$1,"* ]]; return; fi
  grep -q '"error": "http_507' "$HERE/results/$1-$2-t1.0-pg.jsonl" 2>/dev/null
}

for arm in n2 o1 m1 d1; do run "$arm" 8192 3; done

for arm in m1v m1x m1q; do
  run "$arm" 131072 3
  if ! refused "$arm" 131072; then run "$arm" 262144 1; break; fi
done

run d1 131072 3
run d1 262144 1
run d1 524288 1 --yarn 2.0

if [[ -n "$DRY" ]]; then echo "relaunch daily driver"; exit 0; fi
sleep 30
cd "$REPO" && nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > "${ENGINE_G_DRIVER_LOG:-/tmp/flashnext-daily-driver.log}" 2>&1 &
echo "=== SEQ DONE driver diário relançado $(date -u +%H:%M:%S)"
