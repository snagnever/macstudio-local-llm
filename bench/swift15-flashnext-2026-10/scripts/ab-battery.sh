#!/usr/bin/env bash
# Roda as suítes do A/B contra o servidor pronto do run-candidate.sh (BASE_URL, MODEL_ID no ambiente), um
# perfil de sampling após o outro, e copia cada saída para results/<AB_OUT_SUBDIR>/<perfil>/<braço>/<suíte>.jsonl.
# `source ab-battery.sh --lib` só define profile_flags (para os testes).

# t1 = sampling recomendado pelo vendor (generation_config.json dos dois packs + card do Swift 1.5).
# t0 = greedy, o modo das baterias de qualidade anteriores.
profile_flags() {
  case "$1" in
    t1) echo "--temperature 1.0 --top-p 0.95 --top-k 20 --min-p 0 --presence-penalty 0 --repetition-penalty 1.0" ;;
    t0) echo "--temperature 0" ;;
    *) echo "ab-battery: perfil desconhecido: $1" >&2; return 64 ;;
  esac
}
[[ "${1:-}" == --lib ]] && return 0

set -euo pipefail
: "${BASE_URL:?}" "${MODEL_ID:?}" "${AB_ARM:?}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH="${AB_BENCH:-$HOME/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb}"
RUNS="$BENCH/benchmarks/runs"
EFFORT="${AB_EFFORT:-xhigh}"
PROFILES="${AB_PROFILES:-t1 t0}"
SUITES="${AB_SUITES:-humaneval gpqa livecodebench jdhodges veerman if}"
# 65K tokens a ~80 tok/s passam de 800 s: o timeout default (1800 s) fica curto com fila.
export BENCH_TIMEOUT="${BENCH_TIMEOUT:-3600}" TOOLBENCH_MAX_TOKENS="${TOOLBENCH_MAX_TOKENS:-32768}"
newest() { ls -t $RUNS/$1 2>/dev/null | grep -v '_summary\.json$' | head -1; }
rc=0
for p in $PROFILES; do
  FLAGS="$(profile_flags "$p")"
  OUT="$HERE/results/${AB_OUT_SUBDIR:-ab}/$p/$AB_ARM"; mkdir -p "$OUT"
  for s in $SUITES; do
    echo ">>> ab-battery: $AB_ARM $p $s (reasoning_effort=$EFFORT; $FLAGS)"
    case "$s" in
      humaneval|gpqa|livecodebench)
        if [[ "$s" == humaneval ]]; then n=164; mt=32768; else n=50; mt=65536; fi
        (cd "$BENCH" && LMSTUDIO_URL="$BASE_URL" .venv/bin/python scripts/bench2.py "$s" --examples "$n" \
          --model "$MODEL_ID" --max-tokens "$mt" --reasoning-effort "$EFFORT" $FLAGS \
          ${AB_ONLY:+--only "$AB_ONLY"}) || rc=$?
        cp "$(newest "${s}_*.jsonl")" "$OUT/$s.jsonl" ;;
      jdhodges|veerman)
        (cd "$BENCH" && uv run --no-project --with openai --with pyyaml python scripts/tool_call_bench.py \
          --model "$MODEL_ID" --suite "$s" --base-url "$BASE_URL" --run-prefix "toolcall_ab_${p}_$AB_ARM" \
          --no-cooldown --force --reasoning-effort "$EFFORT" $FLAGS) || rc=$?
        cp "$(newest "toolcall_ab_${p}_${AB_ARM}_${s}_*.jsonl")" "$OUT/$s.jsonl" ;;
      if)
        python3 "$HERE/scripts/if_probe.py" --base-url "$BASE_URL" --model "$MODEL_ID" --arm "$AB_ARM" \
          --reasoning-effort "$EFFORT" $FLAGS --output "$OUT/if.jsonl" || rc=$? ;;
      samplecheck)
        # Mesmo prompt 3 vezes: em t0 as respostas devem sair iguais; em t1, ao menos duas diferentes.
        python3 "$HERE/scripts/if_probe.py" --base-url "$BASE_URL" --model "$MODEL_ID" --arm "$AB_ARM" \
          --reasoning-effort "$EFFORT" $FLAGS --only if07 --repeat 3 --output "$OUT/samplecheck.jsonl" || rc=$? ;;
      *) echo "suíte desconhecida: $s" >&2; exit 64 ;;
    esac
  done
done
exit "$rc"
