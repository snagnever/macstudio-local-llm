#!/usr/bin/env bash
# Build a pack overlay: every file of <src_dir> hardlinked into <dst_dir>, except chat_template.jinja, which is
# a copy of <template>. The weights take no extra disk and the source pack does not change.
# When tokenizer_config.json carries a chat_template equal to the source chat_template.jinja, the overlay gets a
# copy of tokenizer_config.json with that key set to <template> too. Exit 65 when the key holds anything else.
# Rerunning with the same template is a no-op; a different template in an existing overlay is refused (exit 73).
# usage: make-overlay.sh <src_dir> <dst_dir> <template>
set -euo pipefail
SRC="${1:?usage: $0 <src_dir> <dst_dir> <template>}"; DST="${2:?dst_dir}"; TPL="${3:?template}"
[[ -d "$SRC" && -f "$TPL" ]] || { echo "make-overlay: missing $SRC or $TPL" >&2; exit 66; }
TOKCFG=""
if [[ -f "$SRC/tokenizer_config.json" ]] && grep -q '"chat_template"' "$SRC/tokenizer_config.json"; then
  python3 -c 'import json,sys; t=json.load(open(sys.argv[1])).get("chat_template"); sys.exit(0 if t == open(sys.argv[2]).read() else 1)' \
    "$SRC/tokenizer_config.json" "$SRC/chat_template.jinja" \
    || { echo "make-overlay: $SRC/tokenizer_config.json has a chat_template that differs from chat_template.jinja" >&2; exit 65; }
  TOKCFG=1
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
if [[ -n "$TOKCFG" ]]; then
  rm -f "$DST/tokenizer_config.json"
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["chat_template"]=open(sys.argv[2]).read(); json.dump(d, open(sys.argv[3], "w"), ensure_ascii=False, indent=2)' \
    "$SRC/tokenizer_config.json" "$TPL" "$DST/tokenizer_config.json"
fi
printf 'source: %s\ntemplate: %s\ntemplate md5: %s\n' "$SRC" "$TPL" "$(md5 -q "$TPL" 2>/dev/null || md5sum "$TPL" | cut -d' ' -f1)" \
  > "$DST/OVERLAY.txt"
echo "make-overlay: $DST ready"
