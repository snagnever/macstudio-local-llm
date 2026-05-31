#!/bin/bash
# Install the tool-aware chat template + json_tools parser into the live model dir.
# Backs up pristine originals to ./original/ (only if not already present), then
# installs. Reverse with uninstall.sh. See
# docs/benchmark-plans/2026-05-30-deepseek-v4-flash-tool-template.md
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELDIR=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ
PY=/Users/vitor/LocalProjects/local-llms/venvs/mlx-v4-flash/bin/python

mkdir -p "$HERE/original"
[ -f "$HERE/original/chat_template.jinja" ]   || cp "$MODELDIR/chat_template.jinja"   "$HERE/original/chat_template.jinja"
[ -f "$HERE/original/tokenizer_config.json" ] || cp "$MODELDIR/tokenizer_config.json" "$HERE/original/tokenizer_config.json"
echo "pristine originals preserved in $HERE/original/"

cp "$HERE/chat_template.jinja" "$MODELDIR/chat_template.jinja"
"$PY" - "$MODELDIR/tokenizer_config.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["tool_parser_type"] = "json_tools"
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
print("tokenizer_config.json: tool_parser_type=json_tools")
PY
echo "INSTALLED tool template into $MODELDIR"
echo "Restart mlx_lm.server for it to take effect."
