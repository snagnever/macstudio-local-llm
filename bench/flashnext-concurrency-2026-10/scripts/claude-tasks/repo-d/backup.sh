#!/usr/bin/env bash
# backup.sh - archive a directory into <dest>/<name>-<YYYYmmdd-HHMMSS>.tar.gz
#
# The archive is a gzip-compressed tarball of SOURCE. The directory itself is
# stored, not just its contents, so restoring recreates it under the target.
# Next to the archive a "<archive>.sha256" sidecar is written in the format
# produced by `shasum -a 256` ("<hex digest>  <file name>"), which verify.sh
# and the stock `shasum -c` command can both check.
#
# On success the absolute path of the new archive is printed on stdout.
# See docs/USAGE.md for the long version of this help.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib/log.sh"

usage() {
  cat <<'EOF'
usage: backup.sh [--dest DIR] [--name NAME] [--quiet] [--dry-run] SOURCE

Archive the directory SOURCE into DIR/NAME-<YYYYmmdd-HHMMSS>.tar.gz and write
a NAME-<stamp>.tar.gz.sha256 sidecar next to it.

options:
  --dest DIR     directory that receives the archive (default: ./backups,
                 created on demand)
  --name NAME    archive base name (default: the basename of SOURCE)
  -q, --quiet    only warnings and errors on stderr
  -n, --dry-run  show what would be archived, write nothing
  -h, --help     show this help and exit

environment:
  BACKUP_STAMP   override the timestamp part of the archive name
                 (format YYYYmmdd-HHMMSS; meant for tests)
  VERBOSE        0, 1 or 2 (see lib/log.sh)

exit codes:
  0 archive written   1 bad usage   2 source or destination problem
  3 tar or shasum failed
EOF
}

# backup.sh has no private options; everything it needs is in the shared
# parser below.
parse_local_option() {
  return 1
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
  die 1 "exactly one SOURCE directory is required"
fi

src=$(resolve_dir "${ARGS[0]}")
[[ -r "$src" ]] || die 2 "source is not readable: $src"

dest="${DEST:-./backups}"
if [[ ! -d "$dest" ]]; then
  if [[ $DRY_RUN -eq 1 ]]; then
    log_info "would create destination $dest"
  else
    mkdir -p "$dest" || die 2 "cannot create destination: $dest"
    log_debug "created destination $dest"
  fi
fi
if [[ -d "$dest" ]]; then
  dest=$(resolve_dir "$dest")
fi

name="${NAME:-$(basename "$src")}"
case "$name" in
  '')  die 1 "--name must not be empty" ;;
  */*) die 1 "--name must not contain '/': $name" ;;
esac

stamp="${BACKUP_STAMP:-$(date +%Y%m%d-%H%M%S)}"
if ! [[ "$stamp" =~ ^[0-9]{8}-[0-9]{6}$ ]]; then
  die 1 "BACKUP_STAMP must look like YYYYmmdd-HHMMSS, got '$stamp'"
fi

archive="$name-$stamp.tar.gz"
if [[ -e "$dest/$archive" ]]; then
  die 2 "refusing to overwrite existing archive: $dest/$archive"
fi

# tar is pointed at the parent so the archive contains "<leaf>/..." entries
# and nothing above it.
parent=$(dirname "$src")
leaf=$(basename "$src")

if [[ $DRY_RUN -eq 1 ]]; then
  log_info "would run: tar -czf '$dest/$archive' -C '$parent' '$leaf'"
  log_info "would write: $dest/$archive.sha256"
  echo "$dest/$archive"
  exit 0
fi

log_info "archiving $src -> $dest/$archive"
if ! tar -czf "$dest/$archive" -C "$parent" "$leaf"; then
  rm -f "$dest/$archive"
  die 3 "tar failed; partial archive removed"
fi

# The sidecar is produced from inside the destination so that it records the
# bare file name, not whatever path we happened to use. That keeps it valid
# when the directory is moved or mounted elsewhere.
if ! (cd "$dest" && shasum -a 256 "$archive" > "$archive.sha256"); then
  rm -f "$dest/$archive" "$dest/$archive.sha256"
  die 3 "shasum failed; archive and sidecar removed"
fi

size=$(wc -c < "$dest/$archive" | tr -d ' ')
log_info "wrote $archive ($size bytes) and $archive.sha256"
echo "$dest/$archive"
