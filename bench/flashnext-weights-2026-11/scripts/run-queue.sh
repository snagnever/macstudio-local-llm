#!/usr/bin/env bash
# Run the flashnext-weights-2026-11 queue in priority order: speed, battery and tool calls of one arm, then the next arm.
# A failing step does not stop the queue; its exit code is printed. Free disk below QUEUE_MIN_FREE_GB stops the queue with exit 3.
# usage: run-queue.sh <f|g> [--dry-run]    (f = Splash 1.5.0, g = Splash 1.6.0)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
RELEASE="${1:-}"; DRY=""
[[ "${2:-}" == --dry-run ]] && DRY=1
case "$RELEASE" in f|g) ;; *) echo "usage: $0 <f|g> [--dry-run]" >&2; exit 64 ;; esac
SUITES="humaneval gpqa livecodebench if jdhodges veerman"
# k7 (ThinkingCap IQ4_XS) left the queue in W0: Splash 1.5.0 and 1.6.0 refuse its hc_*_inject IQ4_XS tensors.
ORDER=(k6 k1 k5 k8 k4 k3)
# Splash 1.6.0 reuses the k2g results of splash16 Tasks 2 and 6; those tasks do not measure k2f with this battery.
[[ "$RELEASE" == f ]] && ORDER=(k2 "${ORDER[@]}")
step() {
  if [[ -n "$DRY" ]]; then echo "$*"; return; fi
  echo "=== $(date '+%F %T') $*"
  bash "$REPO/bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh" --minutes 10 || echo "idle-gate exit=$?"
  rc=0; env "${ENVV[@]}" bash "$@" || rc=$?
  echo "=== $(date '+%F %T') exit=$rc"
}
for stem in "${ORDER[@]}"; do
  free_gb="$(df -g "$HERE" | awk 'NR==2 {print $4}')"
  if [[ "$free_gb" -lt "${QUEUE_MIN_FREE_GB:-150}" ]]; then echo "QUEUE-STOP: free disk ${free_gb} GB" >&2; exit 3; fi
  arm="$stem$RELEASE"
  ENVV=(QUEUE=1); step "$HERE/scripts/run-arm.sh" "$arm" 262144 --repeat 3 --tag w1
  ENVV=("BATTERY_CAMPAIGN_DIR=$HERE")
  step "$REPO/bench/flashnext-next-steps-2026-10/scripts/run-battery.sh" "$arm" w1 --suites "$SUITES" --ctx 262144
  ENVV=("TOOLCALL_CAMPAIGN_DIR=$HERE")
  step "$REPO/bench/stack-updates-2026-10/scripts/toolcall-probe.sh" "$arm" --sessions 20 --suffix w1 --max-tokens 2048
  echo "CHECKPOINT-$arm"
done
echo "CHAIN-weights: done"
