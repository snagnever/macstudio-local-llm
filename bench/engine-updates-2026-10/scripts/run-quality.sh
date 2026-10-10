#!/usr/bin/env bash
# Etapa G4: qualidade barata de um braço (HumanEval 164 + tool-calling jdhodges 40 + Veerman 12, temp 0).
# Sobe o servidor pelo run-candidate.sh (--exec no lugar do probe) e roda os runners do
# submódulo tools/local-llm-bench-m4-32gb do checkout principal. ENGINE_BAND_DRY=1 só imprime.
set -euo pipefail
ARM="${1:?uso: $0 <braço> <ctx>}"; CTX="${2:?ctx}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH="${ENGINE_QUALITY_BENCH:-$HOME/LocalProjects/local-llms/tools/local-llm-bench-m4-32gb}"
EXEC="cd '$BENCH' && LMSTUDIO_URL=\"\$BASE_URL\" .venv/bin/python scripts/bench2.py humaneval --examples 164 --model \"\$MODEL_ID\""
for s in jdhodges veerman; do
  EXEC+=" && uv run --no-project --with openai --with pyyaml python scripts/tool_call_bench.py --model \"\$MODEL_ID\""
  EXEC+=" --suite $s --base-url \"\$BASE_URL\" --run-prefix toolcall_pg_$ARM --no-cooldown --force"
done
if [[ -n "${ENGINE_BAND_DRY:-}" ]]; then echo "EXEC=$EXEC"; echo "bash run-arm.sh $ARM $CTX --tag qual --exec \"\$EXEC\""; exit 0; fi
exec bash "$HERE/scripts/run-arm.sh" "$ARM" "$CTX" --tag qual --exec "$EXEC"
