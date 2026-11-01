#!/usr/bin/env bash
# restore.sh - extract an archive written by backup.sh into a target directory.
#
# ARCHIVE is either a path to a .tar.gz file or a bare file name that is looked
# up inside --dest. When a .sha256 sidecar sits next to the archive it is
# checked first and a mismatch aborts the restore; without a sidecar the script
# warns and continues. With --list the contents are printed instead of
# extracted, which is the quickest way to see what a backup holds.
#
# On success the absolute path of the target directory is printed on stdout.
# See docs/USAGE.md for the long version of this help.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib/log.sh"

usage() {
  cat <<'EOF'
usage: restore.sh [--dest DIR] [--target DIR] [--list] [--dry-run] [--quiet] ARCHIVE

Extract ARCHIVE (a path, or a file name inside --dest) into --target.

options:
  --dest DIR     directory where a bare ARCHIVE name is looked up
  --target DIR   directory to extract into (default: ., created on demand)
  -l, --list     list the archive contents instead of extracting
  -n, --dry-run  show what would be extracted, write nothing
  -q, --quiet    only warnings and errors on stderr
  -h, --help     show this help and exit

exit codes:
  0 restored (or listed)   1 bad usage   2 archive missing or checksum mismatch
  3 tar failed
EOF
}

TARGET=""
LIST=0

# Private options of restore.sh. CONSUMED tells the shared parser how many
# words to drop.
parse_local_option() {
  case "$1" in
    --target)   need_value "$@"; TARGET="$2"; CONSUMED=2 ;;
    --target=*) TARGET="${1#*=}"; CONSUMED=1 ;;
    -l|--list)  LIST=1; CONSUMED=1 ;;
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
if [[ ${#ARGS[@]} -ne 1 ]]; then
  usage >&2
  die 1 "exactly one ARCHIVE is required"
fi

arg="${ARGS[0]}"
if [[ -f "$arg" ]]; then
  # A path was given; make it absolute so log lines stay meaningful after cd.
  archive="$(resolve_dir "$(dirname "$arg")")/$(basename "$arg")"
elif [[ -n "$DEST" ]]; then
  dest=$(resolve_dir "$DEST")
  archive="$dest/$arg"
  [[ -f "$archive" ]] || die 2 "archive not found: $archive"
else
  die 2 "archive not found: $arg (pass --dest DIR to look it up by name)"
fi

base=$(basename "$archive")
case "$base" in
  *.tar.gz|*.tgz) ;;
  *) log_warn "$base does not end in .tar.gz; trying anyway" ;;
esac

# Checksum gate. A sidecar is optional but when present it must match.
sidecar="$archive.sha256"
if [[ -f "$sidecar" ]]; then
  expected=$(awk 'NR == 1 {print $1}' "$sidecar")
  actual=$(shasum -a 256 "$archive" | awk '{print $1}')
  if [[ -z "$expected" || "$expected" != "$actual" ]]; then
    die 2 "checksum mismatch for $base; refusing to restore"
  fi
  log_info "checksum ok for $base"
else
  log_warn "no .sha256 sidecar next to $base; restoring unverified"
fi

if [[ $LIST -eq 1 ]]; then
  log_info "contents of $base"
  tar -tzf "$archive" || die 3 "tar could not read $base"
  exit 0
fi

target="${TARGET:-.}"
if [[ $DRY_RUN -eq 1 ]]; then
  log_info "would extract $base into $target:"
  tar -tzf "$archive" || die 3 "tar could not read $base"
  exit 0
fi

if [[ ! -d "$target" ]]; then
  mkdir -p "$target" || die 2 "cannot create target: $target"
  log_debug "created target $target"
fi
target=$(resolve_dir "$target")

log_info "extracting $base into $target"
tar -xzf "$archive" -C "$target" || die 3 "tar failed while extracting $base"

count=$(tar -tzf "$archive" | wc -l | tr -d ' ')
log_info "restored $count entr$( [[ "$count" -eq 1 ]] && echo y || echo ies ) into $target"
echo "$target"
