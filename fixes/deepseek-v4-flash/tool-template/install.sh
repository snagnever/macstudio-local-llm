#!/bin/bash
# Install the tool-aware chat template + json_tools parser into the live model dir.
# Backs up pristine originals to ./original/ (only if not already present), then
# installs. Reverse with uninstall.sh. See
# bench/deepseek-v4-flash/plan-tool-template.md
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELDIR=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
VENV=/Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash
PY=$VENV/bin/python
PARSERS="$VENV/lib/python3.12/site-packages/mlx_lm/tool_parsers"

mkdir -p "$HERE/original"
[ -f "$HERE/original/chat_template.jinja" ]   || cp "$MODELDIR/chat_template.jinja"   "$HERE/original/chat_template.jinja"
[ -f "$HERE/original/tokenizer_config.json" ] || cp "$MODELDIR/tokenizer_config.json" "$HERE/original/tokenizer_config.json"
echo "pristine originals preserved in $HERE/original/"

# 1. tool-aware chat template
cp "$HERE/chat_template.jinja" "$MODELDIR/chat_template.jinja"
# 2. custom tool parser into the mlx-lm venv (survives the '>' BPE merge)
cp "$HERE/deepseek_json.py" "$PARSERS/deepseek_json.py"
echo "deployed parser -> $PARSERS/deepseek_json.py"
# 3. point tokenizer_config at it
"$PY" - "$MODELDIR/tokenizer_config.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["tool_parser_type"] = "deepseek_json"
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
print("tokenizer_config.json: tool_parser_type=deepseek_json")
PY
echo "INSTALLED tool template + parser into $MODELDIR"
echo "Restart mlx_lm.server for it to take effect."
