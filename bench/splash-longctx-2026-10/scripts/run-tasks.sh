#!/usr/bin/env bash
# Unattended speed queues of the campaign, one server at a time, with idle-gate.sh between bands.
#   t1   Task 1: k1a, k2a, w1z at 8K and k1a, k2a at 256K (3 reps); K3=1 adds k3a at 8K, 32K, 128K and 256K.
#   t2a  Task 2 sweep at 512K, 1 rep: k2a, k2ab and w1zq4 (YaRN 2.0), tag sw.
#   t2b  Task 2 at 512K, 3 reps: SW (k2a or k2ab, the chosen Swift KV), w1zq4 and k1a; K3=1 adds k3a (or k3ab).
#   t3   Task 3 at 1000000, 1 rep: SW and k1a; K3=1 adds k3a.
# The 32K and 128K bands of k1a, k2a and w1z come from bench/stack-updates-2026-10 (Tasks 1, 5 and 8).
# A failing arm does not stop the queue (run-seq.sh prints its exit code). Lines "=== task <t> done" mark the end.
# usage: [K3=1] [SW=k2a|k2ab|k2as] run-tasks.sh <t1|t2a|t2b|t3> [...] [--dry-run]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATE="$HERE/../flashnext-next-steps-2026-10/scripts/idle-gate.sh"
SEQ="$HERE/scripts/run-seq.sh"
K3="${K3:-}"; SW="${SW:-k2a}"
DRY=""; TASKS=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    t1|t2a|t2b|t3) TASKS+=("$a") ;;
    *) echo "usage: $0 <t1|t2a|t2b|t3> [...] [--dry-run]" >&2; exit 64 ;;
  esac
done
[[ ${#TASKS[@]} -gt 0 ]] || { echo "usage: $0 <t1|t2a|t2b|t3> [...] [--dry-run]" >&2; exit 64; }
[[ "$SW" =~ ^k2a(b|s)?$ ]] || { echo "run-tasks: SW must be k2a, k2ab or k2as" >&2; exit 64; }
K3ARM=k3a; [[ "$SW" == k2ab ]] && K3ARM=k3ab

run() { if [[ -n "$DRY" ]]; then echo "$*"; else echo "=== $(date '+%F %T') $*"; "$@"; echo "=== rc=$?"; fi; }
gate() { run bash "$GATE"; }
k3() { [[ -n "$K3" ]] && echo "$@"; }

for t in "${TASKS[@]}"; do
  case "$t" in
    t1) gate; run bash "$SEQ" k1a:8192:3:lc k2a:8192:3:lc w1z:8192:3:lc $(k3 k3a:8192:3:lc k3a:32768:3:lc k3a:131072:3:lc)
        gate; run bash "$SEQ" k1a:262144:3:lc k2a:262144:3:lc $(k3 k3a:262144:3:lc) ;;
    t2a) gate; run bash "$SEQ" k2a:524288:1:sw k2ab:524288:1:sw w1zq4:524288:1:sw:2.0 ;;
    t2b) gate; run bash "$SEQ" "$SW:524288:3:lc" w1zq4:524288:3:lc:2.0 k1a:524288:3:lc $(k3 "$K3ARM:524288:3:lc") ;;
    t3) gate; run bash "$SEQ" "$SW:1000000:1:lc" k1a:1000000:1:lc $(k3 "$K3ARM:1000000:1:lc") ;;
  esac
  echo "=== task $t done $(date '+%F %T')"
done
