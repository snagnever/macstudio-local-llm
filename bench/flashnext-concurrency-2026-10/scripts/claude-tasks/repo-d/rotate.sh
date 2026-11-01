#!/usr/bin/env bash
# rotate.sh - keep the newest KEEP archives of a name, delete the rest.
#
# Archives are the files <dest>/<name>-<YYYYmmdd-HHMMSS>.tar.gz written by
# backup.sh. Age is taken from the timestamp in the file name, never from the
# mtime, so copying a directory of archives around (which resets mtimes) does
# not change what gets rotated. Each deleted archive takes its .sha256 sidecar
# with it. Files that do not follow the naming convention are never touched.
#
# One line per removed archive is printed on stdout: "deleted <file name>"
# (or "would delete <file name>" with --dry-run).
# See docs/USAGE.md for the long version of this help.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib/log.sh"

usage() {
  cat <<'EOF'
usage: rotate.sh --dest DIR --name NAME [--keep N] [--dry-run] [--quiet]

Delete every archive called NAME-<stamp>.tar.gz in DIR except the N newest
(by the timestamp in the name). Sidecars are removed together with their
archive.

options:
  --dest DIR     directory holding the archives (required)
  --name NAME    archive base name, as given to backup.sh (required)
  --keep N       how many archives to keep (default: 5, must be >= 1)
  -n, --dry-run  print what would be deleted, delete nothing
  -q, --quiet    only warnings and errors on stderr
  -h, --help     show this help and exit

exit codes:
  0 done (also when there was nothing to delete)   1 bad usage
  2 destination missing
EOF
}

# rotate.sh has no private options.
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
if [[ ${#ARGS[@]} -ne 0 ]]; then
  usage >&2
  die 1 "rotate.sh takes no positional arguments"
fi
[[ -n "$DEST" ]] || { usage >&2; die 1 "--dest is required"; }
[[ -n "$NAME" ]] || { usage >&2; die 1 "--name is required"; }

dest=$(resolve_dir "$DEST")
keep="${KEEP:-5}"
if [[ "$keep" -lt 1 ]]; then
  die 1 "--keep must be at least 1; refusing to delete every archive"
fi

# list_archives
# One absolute path per line, sorted by the timestamp embedded in the name.
# Only names following the backup.sh convention are considered, so a stray
# "notes.tar.gz" or "<name>.tar.gz" in the destination is never a candidate.
list_archives() {
  find "$dest" -maxdepth 1 -type f -name "$NAME-[0-9]*-[0-9]*.tar.gz" | sort
}

total=$(list_archives | wc -l | tr -d ' ')
log_info "$total archive(s) named '$NAME' in $dest, keeping $keep"

if [[ "$total" -lt "$keep" ]]; then
  log_info "nothing to rotate"
  exit 0
fi

# Everything past the KEEP-th entry of the sorted list is surplus.
surplus() {
  list_archives | tail -n +"$keep"
}

deleted=0
while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  base=$(basename "$path")
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "would delete $base"
  else
    rm -f -- "$path" "$path.sha256"
    log_debug "removed $path and its sidecar"
    echo "deleted $base"
  fi
  deleted=$((deleted + 1))
done < <(surplus)

remaining=$((total - deleted))
if [[ $DRY_RUN -eq 1 ]]; then
  log_info "dry run: $deleted archive(s) would be removed, $remaining would remain"
else
  log_info "removed $deleted archive(s), $remaining remain"
fi
