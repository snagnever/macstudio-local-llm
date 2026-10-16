#!/usr/bin/env bash
# Build a pack overlay: every file of <src_dir> hardlinked into <dst_dir>, except chat_template.jinja, which is
# a copy of <template>. The weights take no extra disk and the source pack does not change.
# Exit 65 when tokenizer_config.json carries a chat_template (the server could read that one instead).
# Rerunning with the same template is a no-op; a different template in an existing overlay is refused (exit 73).
# usage: make-overlay.sh <src_dir> <dst_dir> <template>
set -euo pipefail
SRC="${1:?usage: $0 <src_dir> <dst_dir> <template>}"; DST="${2:?dst_dir}"; TPL="${3:?template}"
[[ -d "$SRC" && -f "$TPL" ]] || { echo "make-overlay: missing $SRC or $TPL" >&2; exit 66; }
if [[ -f "$SRC/tokenizer_config.json" ]] && grep -q '"chat_template"' "$SRC/tokenizer_config.json"; then
  echo "make-overlay: $SRC/tokenizer_config.json has a chat_template; overlay would not take effect" >&2; exit 65
fi
if [[ -d "$DST" ]]; then
  if cmp -s "$TPL" "$DST/chat_template.jinja"; then echo "make-overlay: $DST is up to date"; exit 0; fi
  echo "make-overlay: $DST exists with another template" >&2; exit 73
fi
mkdir -p "$DST"
for f in "$SRC"/*; do
  [[ -f "$f" ]] && ln "$f" "$DST/$(basename "$f")"
done
rm -f "$DST/chat_template.jinja"
cp "$TPL" "$DST/chat_template.jinja"
printf 'source: %s\ntemplate: %s\ntemplate md5: %s\n' "$SRC" "$TPL" "$(md5 -q "$TPL" 2>/dev/null || md5sum "$TPL" | cut -d' ' -f1)" \
  > "$DST/OVERLAY.txt"
echo "make-overlay: $DST ready"
