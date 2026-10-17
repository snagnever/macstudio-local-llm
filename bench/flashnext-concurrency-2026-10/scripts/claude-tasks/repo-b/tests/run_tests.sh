#!/usr/bin/env bash
# Tests for wc_report.sh. usage: bash tests/run_tests.sh (from the repository root)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
check() {  # name expected actual
  if [[ "$2" == "$3" ]]; then echo "ok   $1"; else echo "FAIL $1"; echo "  expected: $2"; echo "  actual:   $3"; fails=$((fails + 1)); fi
}

t=$(mktemp -d)
printf 'one two three\n' > "$t/a.txt"
printf 'one\n' > "$t/b.txt"
check "ranks two files" "3 a.txt
1 b.txt" "$(bash "$ROOT/wc_report.sh" "$t")"
rm -rf "$t"

[[ $fails -eq 0 ]] && echo "all tests passed" || { echo "$fails test(s) failed"; exit 1; }
