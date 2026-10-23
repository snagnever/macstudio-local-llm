#!/usr/bin/env bash
# Unattended queues of the campaign, one server at a time, with idle-gate.sh between bands.
#   t1  Task 1 speed: w1 x w1z at 32K and 128K (3 reps, order alternates) and 256K (1 rep).
#   t4  Task 4 speed: n2z x t6z, same bands; then the quality battery (humaneval livecodebench if) of t6z and n2z.
#   t5  Task 5 speed: k1 and k1a at 32K and 128K (3 reps); reference w1 comes from t1.
#   t6  Task 6: r1 at 32K and 128K (3 reps), tool-call probe, battery (humaneval livecodebench) of r1 and w1.
#   t8  Task 8: k2 x k2a (Swift 1.5 GGUF on Splash) at 32K and 128K (3 reps), k2a at 256K (1 rep), tool-call probe
#       and battery (humaneval livecodebench) of k2a; references w1 (t1, t6) and k1/k1a (t5).
# A failing arm does not stop the queue (run-seq.sh prints its exit code). Lines "=== task <t> done" mark the end.
# usage: run-tasks.sh <t1|t4|t5|t6|t8> [...] [--dry-run]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATE="$HERE/../flashnext-next-steps-2026-10/scripts/idle-gate.sh"
SEQ="$HERE/scripts/run-seq.sh"
BATTERY="$HERE/../flashnext-next-steps-2026-10/scripts/run-battery.sh"
DRY=""; TASKS=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    t1|t4|t5|t6|t8) TASKS+=("$a") ;;
    *) echo "usage: $0 <t1|t4|t5|t6|t8> [...] [--dry-run]" >&2; exit 64 ;;
  esac
done
[[ ${#TASKS[@]} -gt 0 ]] || { echo "usage: $0 <t1|t4|t5|t6|t8> [...] [--dry-run]" >&2; exit 64; }

run() { if [[ -n "$DRY" ]]; then echo "$*"; else echo "=== $(date '+%F %T') $*"; "$@"; echo "=== rc=$?"; fi; }
gate() { run bash "$GATE"; }
battery() { run env BATTERY_CAMPAIGN_DIR="$HERE" bash "$BATTERY" "$@"; }
speed() {  # speed <ref> <cand> <tag>: 32K ref->cand, 128K cand->ref, 256K ref->cand
  gate; run bash "$SEQ" "$1:32768:3:$3" "$2:32768:3:$3"
  gate; run bash "$SEQ" "$2:131072:3:$3" "$1:131072:3:$3"
  gate; run bash "$SEQ" "$1:262144:1:$3" "$2:262144:1:$3"
}

for t in "${TASKS[@]}"; do
  case "$t" in
    t1) speed w1 w1z e1 ;;
    t4) speed n2z t6z e4
        gate; battery t6z e4 --suites "humaneval livecodebench if"
        gate; battery n2z e4 --suites "humaneval livecodebench if" ;;
    t5) gate; run bash "$SEQ" k1:32768:3:e5 k1a:32768:3:e5
        gate; run bash "$SEQ" k1a:131072:3:e5 k1:131072:3:e5 ;;
    t6) gate; run bash "$SEQ" r1:32768:3:e6
        gate; run bash "$SEQ" r1:131072:3:e6
        gate; run bash "$HERE/scripts/toolcall-probe.sh" r1
        gate; battery r1 e6 --suites "humaneval livecodebench"
        gate; battery w1 e6 --suites "humaneval livecodebench" ;;
    t8) gate; run bash "$SEQ" k2:32768:3:e8 k2a:32768:3:e8
        gate; run bash "$SEQ" k2a:131072:3:e8 k2:131072:3:e8
        gate; run bash "$SEQ" k2a:262144:1:e8
        gate; run bash "$HERE/scripts/toolcall-probe.sh" k2a
        gate; battery k2a e6 --suites "humaneval livecodebench" ;;
  esac
  echo "=== task $t done $(date '+%F %T')"
done
