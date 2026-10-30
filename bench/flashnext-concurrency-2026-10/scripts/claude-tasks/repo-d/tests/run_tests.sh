#!/usr/bin/env bash
# Tests for the backup toolkit. usage: bash tests/run_tests.sh (from the repository root)
#
# Each group builds its fixtures in a fresh temporary directory, runs the
# scripts with a fixed BACKUP_STAMP so that file names are predictable, and
# compares the result with `check`. Nothing here depends on the clock or on
# the current working directory. Temporary directories are removed at the end
# of each group.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fails=0
check() {  # name expected actual
  if [[ "$2" == "$3" ]]; then echo "ok   $1"; else echo "FAIL $1"; echo "  expected: $2"; echo "  actual:   $3"; fails=$((fails + 1)); fi
}

# tmpdir: a fresh directory with symlinks resolved, so paths printed by the
# scripts (which use `pwd -P`) compare equal to the ones we build here.
tmpdir() {
  local d
  d=$(mktemp -d)
  (cd "$d" && pwd -P)
}

# --- backup.sh ---------------------------------------------------------------
t=$(tmpdir)
mkdir -p "$t/src/notes"
printf 'hello\n' > "$t/src/hello.txt"
printf 'second file\n' > "$t/src/notes/todo.txt"

out=$(BACKUP_STAMP=20260101-120000 bash "$ROOT/backup.sh" --quiet --dest "$t/dest" --name demo "$t/src")
check "backup names the archive after --name and the stamp" "$t/dest/demo-20260101-120000.tar.gz" "$out"

expected=$(cut -d' ' -f1 "$t/dest/demo-20260101-120000.tar.gz.sha256")
actual=$(shasum -a 256 "$t/dest/demo-20260101-120000.tar.gz" | cut -d' ' -f1)
check "backup writes a sidecar holding the archive digest" "$expected" "$actual"

# --- restore.sh --------------------------------------------------------------
listing=$(bash "$ROOT/restore.sh" --quiet --list --dest "$t/dest" demo-20260101-120000.tar.gz | sort)
check "restore --list shows the archived entries" "src/
src/hello.txt
src/notes/
src/notes/todo.txt" "$listing"

bash "$ROOT/restore.sh" --quiet --target "$t/out" "$t/dest/demo-20260101-120000.tar.gz" > /dev/null
check "restore extracts the files into --target" "hello" "$(cat "$t/out/src/hello.txt")"

# --- verify.sh ---------------------------------------------------------------
check "verify reports ok for an intact archive" "ok demo-20260101-120000.tar.gz" "$(bash "$ROOT/verify.sh" --quiet --dest "$t/dest")"

printf 'x' >> "$t/dest/demo-20260101-120000.tar.gz"   # corrupt the archive, keep the sidecar
rc=0
out=$(bash "$ROOT/verify.sh" --quiet --dest "$t/dest") || rc=$?
check "verify reports BAD and exits 2 for a corrupted archive" "BAD demo-20260101-120000.tar.gz / rc=2" "$out / rc=$rc"
rm -rf "$t"

[[ $fails -eq 0 ]] && echo "all tests passed" || { echo "$fails test(s) failed"; exit 1; }
