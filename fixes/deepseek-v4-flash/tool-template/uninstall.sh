#!/bin/bash
# Restore the pristine original chat template + tokenizer_config into the model dir,
# undoing install.sh. Restart mlx_lm.server afterwards.
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELDIR=/Users/vitor/.lmstudio/models/mlx-community/DeepSeek-V4-Flash-2bit-DQ

if [ ! -f "$HERE/original/chat_template.jinja" ] || [ ! -f "$HERE/original/tokenizer_config.json" ]; then
  echo "ERROR: pristine originals missing in $HERE/original/ — refusing to restore." >&2
  exit 1
fi
cp "$HERE/original/chat_template.jinja"   "$MODELDIR/chat_template.jinja"
cp "$HERE/original/tokenizer_config.json" "$MODELDIR/tokenizer_config.json"
echo "RESTORED original template + tokenizer_config into $MODELDIR"
echo "Restart mlx_lm.server for it to take effect."
