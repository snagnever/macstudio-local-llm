#!/usr/bin/env bash
# report.sh - table of the archives in a directory, largest first.
#
# One row per <name>-<YYYYmmdd-HHMMSS>.tar.gz file: size in bytes, the date
# decoded from the file name, and the file name. Rows are sorted by size with
# the largest archive on top, which is usually the one you want to look at
# when a disk fills up. --top N limits the table to the N largest.
#
# A header row is printed first unless --no-header is given; a summary line
# (count and total bytes) goes to stderr via log_info so stdout stays a table.
# See docs/USAGE.md for the long version of this help.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib/log.sh"

usage() {
  cat <<'EOF'
usage: report.sh --dest DIR [--name NAME] [--top N] [--no-header] [--quiet]

List the archives in DIR as "<size> <date> <name>" rows, largest first.

options:
  --dest DIR     directory holding the archives (required)
  --name NAME    only list archives whose name starts with NAME-
  --top N        show only the N largest archives
  --no-header    omit the SIZE/DATE/NAME header row
  -q, --quiet    only warnings and errors on stderr
  -h, --help     show this help and exit

exit codes:
  0 table printed (possibly empty)   1 bad usage   2 destination missing
EOF
}

TOP=""
HEADER=1

# Private options of report.sh. CONSUMED tells the shared parser how many
# words to drop.
parse_local_option() {
  case "$1" in
    --top)       need_value "$@"; TOP="$2"; CONSUMED=2 ;;
    --top=*)     TOP="${1#*=}"; CONSUMED=1 ;;
    --no-header) HEADER=0; CONSUMED=1 ;;
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# Option parsing.
#
# NOTE: this block is identical in backup.sh, rotate.sh, verify.sh, restore.sh
# and report.sh. Not every script uses every option (--keep means nothing to
# backup.sh, for instance) but the parser is kept whole so that a flag behaves
# the same everywhere. When you change it here, change it in the others too.
#
# Script-specific flags are handled by parse_local_option, which every script
# defines before this block. It must set CONSUMED to the number of words it
# used (1 for a bare flag, 2 for "--flag VALUE") and return 0, or return 1 to
# report an unknown option.
# ---------------------------------------------------------------------------
DEST=""
NAME=""
KEEP=""
QUIET=0
DRY_RUN=0
ARGS=()          # positional arguments, in order
CONSUMED=0       # set by parse_local_option

# is_uint STRING   true for a non-negative decimal integer
is_uint() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

# need_value OPTION [VALUE]   die unless the option received a value
need_value() {
  [[ $# -ge 2 && -n "$2" ]] || die 1 "option $1 requires a value (see --help)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)        need_value "$@"; DEST="$2"; shift 2 ;;
    --dest=*)      DEST="${1#*=}"; shift ;;
    --name)        need_value "$@"; NAME="$2"; shift 2 ;;
    --name=*)      NAME="${1#*=}"; shift ;;
    --keep)        need_value "$@"; KEEP="$2"; shift 2 ;;
    --keep=*)      KEEP="${1#*=}"; shift ;;
    -q|--quiet)    QUIET=1; VERBOSE=0; shift ;;
    -n|--dry-run)  DRY_RUN=1; shift ;;
    -h|--help)     usage; exit 0 ;;
    --)            shift; while [[ $# -gt 0 ]]; do ARGS[${#ARGS[@]}]="$1"; shift; done ;;
    -*)
      CONSUMED=0
      if ! parse_local_option "$@"; then
        usage >&2
        die 1 "unknown option: $1"
      fi
      [[ "$CONSUMED" -ge 1 ]] || die 1 "internal error: parse_local_option consumed nothing for $1"
      shift "$CONSUMED"
      ;;
    *)             ARGS[${#ARGS[@]}]="$1"; shift ;;
  esac
done

if [[ -n "$KEEP" ]] && ! is_uint "$KEEP"; then
  die 1 "--keep expects a non-negative integer, got '$KEEP'"
fi

# resolve_dir PATH
# Print the absolute, symlink-free path of an existing directory, or die.
# Relative paths are taken from the current working directory.
resolve_dir() {
  local p="$1"
  [[ -n "$p" ]] || die 1 "resolve_dir: empty path"
  [[ -d "$p" ]] || die 2 "not a directory: $p"
  (cd "$p" && pwd -P)
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if [[ ${#ARGS[@]} -ne 0 ]]; then
  usage >&2
  die 1 "report.sh takes no positional arguments"
fi
[[ -n "$DEST" ]] || { usage >&2; die 1 "--dest is required"; }
if [[ -n "$TOP" ]] && ! is_uint "$TOP"; then
  die 1 "--top expects a non-negative integer, got '$TOP'"
fi

dest=$(resolve_dir "$DEST")

pattern="*-[0-9]*-[0-9]*.tar.gz"
if [[ -n "$NAME" ]]; then
  pattern="$NAME-[0-9]*-[0-9]*.tar.gz"
fi

# archive_date FILE_NAME
# Decode the YYYYmmdd-HHMMSS part of a backup.sh file name into
# "YYYY-mm-dd HH:MM:SS". Prints "-" when the name does not carry a stamp.
archive_date() {
  local base="$1"
  if [[ "$base" =~ -([0-9]{4})([0-9]{2})([0-9]{2})-([0-9]{2})([0-9]{2})([0-9]{2})\.tar\.gz$ ]]; then
    printf '%s-%s-%s %s:%s:%s' \
      "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" \
      "${BASH_REMATCH[4]}" "${BASH_REMATCH[5]}" "${BASH_REMATCH[6]}"
  else
    printf -- '-'
  fi
}

# raw_rows
# Tab-separated "<size>\t<date>\t<name>" lines, unsorted. Sizes are taken
# with `wc -c` because stat(1) has incompatible flags on macOS and Linux.
raw_rows() {
  find "$dest" -maxdepth 1 -type f -name "$pattern" | while IFS= read -r path; do
    local base size
    base=$(basename "$path")
    size=$(wc -c < "$path" | tr -d ' ')
    printf '%s\t%s\t%s\n' "$size" "$(archive_date "$base")" "$base"
  done
}

# sorted_rows
# Largest first, optionally cut to --top N.
sorted_rows() {
  if [[ -n "$TOP" ]]; then
    raw_rows | sort -r | head -n "$TOP"
  else
    raw_rows | sort -r
  fi
}

count=0
total=0
if [[ $HEADER -eq 1 ]]; then
  printf '%12s  %-19s  %s\n' SIZE DATE NAME
fi
while IFS=$'\t' read -r size date name; do
  [[ -n "$size" ]] || continue
  printf '%12s  %-19s  %s\n' "$size" "$date" "$name"
  count=$((count + 1))
  total=$((total + size))
done < <(sorted_rows)

log_info "$count archive(s) listed, $total bytes"
