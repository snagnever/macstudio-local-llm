#!/usr/bin/env bash
# DeepSeek Harness (dsh) apontado para o rig (provider RIG_PROVIDER registrado
# na secao llm-pi-ai de $DSH_HOME/settings.yaml, um provider por porta). O dsh fixa o effort na
# criacao da sessao e le a selecao default da secao agent-default-model do
# settings.yaml (o config do plugin aceita so provider e model). O launcher
# reescreve essa secao com o modelo e o effort do run e preserva as outras.
# DSH_PROFILE=web (default) abre a UI em http://127.0.0.1:3080 com o
# workspace no diretorio do run; DSH_PROFILE=headless roda uma tarefa e sai.
# Uso: EFFORT=<none|minimal|low|medium|high|xhigh> bench/qwen3.8-harness-eval/macbook/run-dsh-{27b,fn}.sh [dir-do-run] [--print] [args extra do dsh]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DSH_BIN="${DSH_BIN:-dsh}"
DSH_PROFILE="${DSH_PROFILE:-web}"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
DSH_SETTINGS="$DSH_HOME/settings.yaml"

mkdir -p "$DSH_HOME"
python3 - "$DSH_SETTINGS" "$RIG_PROVIDER" "$RIG_MODEL_ID" "$EFFORT" <<'EOF'
import sys
path, provider, model, effort = sys.argv[1:5]
try:
    lines = open(path).read().splitlines()
except FileNotFoundError:
    lines = []
# Drop the existing top-level agent-default-model block; keep everything else.
out, skip = [], False
for line in lines:
    if line[:1] not in (" ", "\t", "") and not line.startswith("#"):
        skip = line.startswith("agent-default-model:")
    if not skip:
        out.append(line)
out += ["agent-default-model:", f"  provider: {provider}", f"  model: {model}", f"  reasoningEffort: {effort}"]
open(path, "w").write("\n".join(out) + "\n")
EOF

export_env DSH_HOME "$DSH_HOME"
export_env RIG_API_KEY "local"
export_env DSH_TELEMETRY_MODE "DISABLED"

launch "$DSH_BIN" --profile "$DSH_PROFILE" "$@"
