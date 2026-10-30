#!/usr/bin/env bash
# check-d.sh REPO - decide whether task d was solved in the repository at REPO.
#
# Prints exactly "true" or "false" on stdout and always exits 0. Everything
# the probed scripts print is discarded. All of the following must hold:
#   (a) `bash tests/run_tests.sh` exits 0 from the repository root
#   (b) tests/run_tests.sh has at least nine `check` calls
#   (c) lib/common.sh exists and at least four top-level scripts source it
#   (d) bug 1: rotate.sh --keep 3 leaves exactly three archives untouched,
#       and with four archives removes the oldest one only
#   (e) bug 2: verify.sh reports "ok" and exits 0 for an archive whose name
#       contains a space and whose sidecar is correct
#   (f) bug 3: report.sh lists a 10000-byte archive before a 9999-byte one
# bash 3.2 compatible.
set -uo pipefail

repo="${1:-}"
tmp=""

cleanup() {
  if [[ -n "$tmp" && -d "$tmp" ]]; then
    rm -rf -- "$tmp"
  fi
}
trap cleanup EXIT

check_all() {
  [[ -n "$repo" && -d "$repo" ]] || return 1
  repo=$(cd "$repo" && pwd -P) || return 1
  [[ -f "$repo/tests/run_tests.sh" ]] || return 1
  [[ -f "$repo/rotate.sh" && -f "$repo/verify.sh" && -f "$repo/report.sh" ]] || return 1

  # (a) the suite passes
  (cd "$repo" && bash tests/run_tests.sh) || return 1

  # (b) at least nine check calls
  local n
  n=$(grep -c '^check ' "$repo/tests/run_tests.sh") || return 1
  [[ "$n" -ge 9 ]] || return 1

  # (c) the shared library exists and is sourced by at least four scripts
  [[ -f "$repo/lib/common.sh" ]] || return 1
  local sourced
  sourced=$(cd "$repo" && grep -l 'source.*lib/common.sh' *.sh | wc -l | tr -d ' ')
  [[ "$sourced" -ge 4 ]] || return 1

  tmp=$(mktemp -d) || return 1

  # (d) bug 1: exactly KEEP archives must all survive a rotation ...
  local d="$tmp/rotate"
  mkdir -p "$d" || return 1
  : > "$d/x-20260101-000000.tar.gz"
  : > "$d/x-20260102-000000.tar.gz"
  : > "$d/x-20260103-000000.tar.gz"
  (cd "$tmp" && bash "$repo/rotate.sh" --dest "$d" --name x --keep 3) || return 1
  [[ -f "$d/x-20260101-000000.tar.gz" ]] || return 1
  [[ -f "$d/x-20260102-000000.tar.gz" ]] || return 1
  [[ -f "$d/x-20260103-000000.tar.gz" ]] || return 1
  # ... and with one more than KEEP, only the oldest goes.
  : > "$d/x-20260104-000000.tar.gz"
  (cd "$tmp" && bash "$repo/rotate.sh" --dest "$d" --name x --keep 3) || return 1
  [[ ! -e "$d/x-20260101-000000.tar.gz" ]] || return 1
  [[ -f "$d/x-20260102-000000.tar.gz" ]] || return 1
  [[ -f "$d/x-20260103-000000.tar.gz" ]] || return 1
  [[ -f "$d/x-20260104-000000.tar.gz" ]] || return 1

  # (e) bug 2: a correct archive whose name contains a space verifies ok
  local v="$tmp/verify"
  mkdir -p "$v/payload" || return 1
  echo "some data" > "$v/payload/file.txt"
  tar -czf "$v/my backup-20260101-000000.tar.gz" -C "$v" payload || return 1
  (cd "$v" && shasum -a 256 "my backup-20260101-000000.tar.gz" > "my backup-20260101-000000.tar.gz.sha256") || return 1
  local out
  out=$(cd "$tmp" && bash "$repo/verify.sh" --dest "$v") || return 1
  printf '%s\n' "$out" | grep -q '^ok ' || return 1
  if printf '%s\n' "$out" | grep -q '^BAD '; then
    return 1
  fi

  # (f) bug 3: 10000 bytes ranks above 9999 bytes
  local r="$tmp/report"
  mkdir -p "$r" || return 1
  head -c 10000 /dev/zero > "$r/big-20260101-000000.tar.gz" || return 1
  head -c 9999 /dev/zero > "$r/small-20260102-000000.tar.gz" || return 1
  out=$(cd "$tmp" && bash "$repo/report.sh" --dest "$r") || return 1
  local first
  first=$(printf '%s\n' "$out" | grep '\.tar\.gz$' | head -n 1)
  [[ "$first" == *big-20260101-000000.tar.gz ]] || return 1

  return 0
}

if check_all >/dev/null 2>&1; then
  echo true
else
  echo false
fi
