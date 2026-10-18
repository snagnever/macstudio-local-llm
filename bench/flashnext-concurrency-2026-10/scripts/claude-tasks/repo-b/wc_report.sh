#!/usr/bin/env bash
# Rank the text files of a directory by word count, largest first.
# usage: wc_report.sh <dir>
# Output: one line per file, "<words> <file name>".
set -euo pipefail
dir="${1:?usage: wc_report.sh <dir>}"
for f in $(ls "$dir"); do
  [[ -f "$dir/$f" ]] || continue
  words=$(wc -w < "$dir/$f" | tr -d ' ')
  echo "$words $f"
done | sort -r
