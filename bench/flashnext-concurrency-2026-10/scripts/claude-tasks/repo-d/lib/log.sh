#!/usr/bin/env bash
# lib/log.sh - logging helpers shared by every script of the backup toolkit.
#
# All messages go to stderr. stdout is reserved for machine-readable output
# (the path of a new archive, report rows, "ok"/"BAD" lines) so that callers
# can pipe it without first filtering out chatter.
#
# Verbosity convention
#   VERBOSE=0   warnings and errors only            (this is what --quiet selects)
#   VERBOSE=1   plus informational messages         (default)
#   VERBOSE=2   plus debug chatter                  (export VERBOSE=2 by hand)
#
# VERBOSE is honoured when it is already set in the environment, so a whole
# pipeline can be silenced with `VERBOSE=0 ./backup.sh ...` instead of passing
# --quiet to each script. The --quiet flag simply sets VERBOSE=0.
#
# This file is meant to be sourced, never executed:
#   source "$(dirname "${BASH_SOURCE[0]}")/lib/log.sh"
#
# Everything here is bash 3.2 compatible (the /bin/bash shipped with macOS):
# no associative arrays, no ${var,,}, no mapfile.

# Guard against double sourcing. A wrapper that sources two toolkit scripts
# would otherwise redefine every function and reset VERBOSE under our feet.
if [[ -n "${__BACKUP_LOG_SH_LOADED:-}" ]]; then
  return 0 2>/dev/null || true
fi
__BACKUP_LOG_SH_LOADED=1

: "${VERBOSE:=1}"

# Name shown in every line. BASH_SOURCE[1] is the script that sourced us; when
# the library is sourced from an interactive shell it falls back to $0.
: "${LOG_PREFIX:=$(basename "${BASH_SOURCE[1]:-$0}")}"

# Timestamp used in front of every message. ISO-like, second resolution, local
# time. Kept in one place so a future `--utc` flag only has to change this.
_log_stamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

# _log_emit LEVEL MESSAGE...
# Low-level writer. Do not call directly; use the log_* wrappers below.
_log_emit() {
  local level="$1"
  shift
  printf '%s [%s] %s: %s\n' "$(_log_stamp)" "$level" "$LOG_PREFIX" "$*" >&2
}

# log_debug MESSAGE...   shown only with VERBOSE>=2
log_debug() {
  [[ "${VERBOSE}" -ge 2 ]] && _log_emit DEBUG "$@"
  return 0
}

# log_info MESSAGE...    shown with VERBOSE>=1 (hidden by --quiet)
log_info() {
  [[ "${VERBOSE}" -ge 1 ]] && _log_emit INFO "$@"
  return 0
}

# log_warn MESSAGE...    always shown
log_warn() {
  _log_emit WARN "$@"
}

# log_error MESSAGE...   always shown
log_error() {
  _log_emit ERROR "$@"
}

# die [EXIT_CODE] MESSAGE...
# Log an error and exit. The first argument is taken as the exit code when it
# is a plain integer, otherwise the code defaults to 1.
#
# Exit code convention used across the toolkit:
#   1  bad usage (unknown flag, missing value, missing argument)
#   2  data problem (source or archive missing, checksum mismatch)
#   3  an external tool failed (tar, gzip, shasum)
die() {
  local code=1
  if [[ $# -gt 1 && "$1" =~ ^[0-9]+$ ]]; then
    code="$1"
    shift
  fi
  log_error "$@"
  exit "$code"
}

# set_quiet
# Equivalent of --quiet for callers that source the library directly.
set_quiet() {
  VERBOSE=0
}

# log_is_quiet
# True when informational messages are suppressed. Handy for scripts that
# want to print a progress summary only in verbose mode.
log_is_quiet() {
  [[ "${VERBOSE}" -lt 1 ]]
}
