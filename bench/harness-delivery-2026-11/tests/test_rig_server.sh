#!/usr/bin/env bash
# Tests for rig-server.sh (--print only: nothing starts). usage: bash tests/test_rig_server.sh
set -uo pipefail
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/rig-server.sh"
fails=0
ok() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fails=$((fails + 1)); fi; }

out="$(bash "$S" start z4 --print 2>&1)"; rc=$?
ok "start z4 --print exits 0" "[[ $rc -eq 0 ]]"
ok "print names the pack" "grep -q 'FLASHNEXT_SPLASH_PACK=z4' <<<\"\$out\""
ok "print pins Splash 1.6.1" "grep -q 'FLASHNEXT_SPLASH_TAG=1.6.1' <<<\"\$out\""
ok "print boots rc2 at 131072" "grep -q 'rc2 131072' <<<\"\$out\""
ok "print holds the server with --exec" "grep -q -- '--exec' <<<\"\$out\""
bash "$S" start z9 --print >/dev/null 2>&1; rc=$?
ok "unknown pack exits 64" "[[ $rc -eq 64 ]]"
bash "$S" bogus >/dev/null 2>&1; rc=$?
ok "unknown command exits 64" "[[ $rc -eq 64 ]]"
for p in k2 z2 z4; do bash "$S" start "$p" --print >/dev/null 2>&1; ok "pack $p accepted" "[[ $? -eq 0 ]]"; done
[[ $fails -eq 0 ]] && echo "all tests passed" || { echo "$fails test(s) failed"; exit 1; }
