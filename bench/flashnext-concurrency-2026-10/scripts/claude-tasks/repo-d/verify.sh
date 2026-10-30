#!/usr/bin/env bash
# verify.sh - recompute the checksum of every archive in a directory and
# compare it with its .sha256 sidecar.
#
# For each "<file>.sha256" sidecar in the destination the script recomputes
# `shasum -a 256` of the archive and prints one line on stdout:
#
#   ok  <file name>     digest matches
#   BAD <file name>     digest differs, archive missing, or sidecar malformed
#
# The exit status is 0 when every archive is ok and 2 as soon as one is BAD,
# so the script can be used directly as a health check in cron or CI.
# See docs/USAGE.md for the long version of this help.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib/log.sh"

usage() {
  cat <<'EOF'
usage: verify.sh --dest DIR [--name NAME] [--quiet]

Check every archive in DIR against its .sha256 sidecar. Prints "ok <file>" or
"BAD <file>" per archive.

options:
  --dest DIR     directory holding the archives and sidecars (required)
  --name NAME    only check archives whose name starts with NAME-
  -q, --quiet    only warnings and errors on stderr
  -h, --help     show this help and exit

exit codes:
  0 every archive ok (or nothing to check)   1 bad usage
  2 at least one BAD archive
EOF
}

# verify.sh has no private options.
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
  die 1 "verify.sh takes no positional arguments"
fi
[[ -n "$DEST" ]] || { usage >&2; die 1 "--dest is required"; }

dest=$(resolve_dir "$DEST")

checked=0
good=0
bad=0

# report_bad FILE [REASON]
report_bad() {
  if [[ $# -gt 1 ]]; then
    echo "BAD $1 ($2)"
  else
    echo "BAD $1"
  fi
  bad=$((bad + 1))
}

for sidecar in "$dest"/*.sha256; do
  # With no match the glob stays literal; skip that pseudo entry.
  [[ -e "$sidecar" ]] || continue

  if [[ -n "$NAME" ]]; then
    case "$(basename "$sidecar")" in
      "$NAME"-*) ;;
      *) continue ;;
    esac
  fi
  checked=$((checked + 1))

  # A sidecar holds one line in shasum format: "<digest>  <file name>".
  line=$(head -n 1 "$sidecar")
  expected=$(echo "$line" | awk '{print $1}')
  file=$(echo "$line" | awk '{print $2}')

  if [[ -z "$expected" || -z "$file" ]]; then
    report_bad "$(basename "$sidecar")" "malformed sidecar"
    continue
  fi
  if [[ ! -f "$dest/$file" ]]; then
    report_bad "$file" "archive missing"
    continue
  fi

  actual=$(shasum -a 256 "$dest/$file" | awk '{print $1}')
  log_debug "$file expected=$expected actual=$actual"

  if [ $expected == $actual ]; then
    echo "ok $file"
    good=$((good + 1))
  else
    report_bad "$file"
  fi
done

if [[ $checked -eq 0 ]]; then
  log_warn "no .sha256 sidecars found in $dest; nothing verified"
  exit 0
fi

log_info "checked $checked archive(s): $good ok, $bad bad"
if [[ $bad -gt 0 ]]; then
  exit 2
fi
