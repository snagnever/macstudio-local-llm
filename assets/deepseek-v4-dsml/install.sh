#!/bin/bash
# Install the NATIVE DSML tool stack for DeepSeek-V4-Flash:
#   - official DSML chat_template.jinja (from deepseek-ai/DeepSeek-V4-Flash PR #16)
#   - deepseek_dsml tool parser into the mlx-lm venv
#   - tokenizer_config tool_parser_type=deepseek_dsml
# Server must run with --chat-template-args '{"thinking_mode":"chat"}' for thinking OFF.
# Reverse with ../deepseek-v4-tool-template/uninstall.sh (restores the pristine original).
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELDIR=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
VENV=/Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash
PY=$VENV/bin/python
PARSERS="$VENV/lib/python3.12/site-packages/mlx_lm/tool_parsers"

cp "$HERE/chat_template.jinja" "$MODELDIR/chat_template.jinja"
cp "$HERE/deepseek_dsml.py" "$PARSERS/deepseek_dsml.py"
echo "deployed parser -> $PARSERS/deepseek_dsml.py"
"$PY" - "$MODELDIR/tokenizer_config.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p)); d["tool_parser_type"] = "deepseek_dsml"
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
print("tokenizer_config.json: tool_parser_type=deepseek_dsml")
PY
echo "INSTALLED native DSML tool stack into $MODELDIR"
echo "Start server with: --chat-template-args '{\"thinking_mode\":\"chat\"}'  (thinking OFF)"
