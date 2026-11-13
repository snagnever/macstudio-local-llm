#!/usr/bin/env bash
# Run one stage of the swift-uncensored-2026-11 campaign on a list of arms, one server at a time.
#   refusal <arm>...  refusal-arm.sh on each arm (give k2h too: it validates the classifier)
#   speed   <z>...    cache_probe at 32768, 131072 and 262144, two boots per arm and band, k2h first and last
#   quality <arm>...  battery, tool calls and long-context probe of each arm at 262144
#   claude  <z>       two Claude Code sessions (rc2, tasks c and d) at 131072: k2, z, z, k2
# A failing step does not stop the queue: an "end <step> rc=<exit>" line records each exit. Free disk below
# QUEUE_MIN_FREE_GB (default 150) stops the queue with exit 3. QUEUE_GAP_S is the pause between steps (default 120);
# QUEUE_IDLE_GATE=0 skips idle-gate.sh.
# usage: run-queue.sh <refusal|speed|quality|claude> <arm> [<arm> ...] [--dry-run]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
usage() { echo "usage: $0 <refusal|speed|quality|claude> <arm> [<arm> ...] [--dry-run]" >&2; exit 64; }
STAGE="${1:-}"; [[ $# -gt 0 ]] && shift
DRY=""; ARMS=()
for a in "$@"; do
  if [[ "$a" == --dry-run ]]; then DRY=1; continue; fi
  case "$STAGE:$a" in
    refusal:k2h|quality:k2h|*:z[0-4]h) ARMS+=("$a") ;;
    *) usage ;;
  esac
done
case "$STAGE" in refusal|speed|quality|claude) ;; *) usage ;; esac
[[ ${#ARMS[@]} -gt 0 ]] || usage
[[ "$STAGE" == claude && ${#ARMS[@]} -ne 1 ]] && usage
SUITES="humaneval gpqa livecodebench if jdhodges veerman"
N=0

# step <label> <printed command> <env assignments, space separated, or ""> <script> [args...]
step() {
  local label="$1" shown="$2" envs="$3"; shift 3
  N=$((N + 1))
  if [[ -n "$DRY" ]]; then echo "$shown"; return; fi
  local free_gb; free_gb="$(df -g "$HERE" | awk 'NR==2 {print $4}')"
  if [[ "$free_gb" -lt "${QUEUE_MIN_FREE_GB:-150}" ]]; then echo "QUEUE-STOP: free disk ${free_gb} GB" >&2; exit 3; fi
  if [[ $N -gt 1 ]]; then sleep "${QUEUE_GAP_S:-120}"; fi
  if [[ "${QUEUE_IDLE_GATE:-1}" != 0 ]]; then
    bash "$REPO/bench/flashnext-next-steps-2026-10/scripts/idle-gate.sh" --minutes 10 || echo "idle-gate exit=$?"
  fi
  echo "=== $(date '+%F %T') start $label"
  local rc=0
  # shellcheck disable=SC2086
  env $envs bash "$@" || rc=$?
  echo "=== $(date '+%F %T') end $label rc=$rc"
}

speed_step() {  # <arm> <ctx>
  local tag="s$((N + 1))"
  step "$1@$2" "run-arm.sh $1 $2 --repeat 1 --tag $tag" "" "$HERE/scripts/run-arm.sh" "$1" "$2" --repeat 1 --tag "$tag"
}

case "$STAGE" in
  refusal)
    for arm in "${ARMS[@]}"; do
      step "refusal $arm" "refusal-arm.sh $arm" "" "$HERE/scripts/refusal-arm.sh" "$arm"
    done ;;
  speed)
    REV=(); for ((i = ${#ARMS[@]} - 1; i >= 0; i--)); do REV+=("${ARMS[i]}"); done
    for ctx in 32768 131072 262144; do
      if [[ "$ctx" == 131072 ]]; then ORDER=("${REV[@]}" k2h k2h "${ARMS[@]}"); else ORDER=(k2h "${ARMS[@]}" "${REV[@]}" k2h); fi
      for arm in "${ORDER[@]}"; do speed_step "$arm" "$ctx"; done
    done ;;
  quality)
    for arm in "${ARMS[@]}"; do
      step "battery $arm" "run-battery.sh $arm su1 --suites \"$SUITES\" --ctx 262144" "BATTERY_CAMPAIGN_DIR=$HERE" \
        "$REPO/bench/flashnext-next-steps-2026-10/scripts/run-battery.sh" "$arm" su1 --suites "$SUITES" --ctx 262144
      step "toolcalls $arm" "toolcall-probe.sh $arm --sessions 20 --suffix su1 --max-tokens 2048" "TOOLCALL_CAMPAIGN_DIR=$HERE" \
        "$REPO/bench/stack-updates-2026-10/scripts/toolcall-probe.sh" "$arm" --sessions 20 --suffix su1 --max-tokens 2048
      step "longctx $arm" "longctx-arm.sh $arm 262144 131072 262144" "" "$HERE/scripts/longctx-arm.sh" "$arm" 262144 131072 262144
    done ;;
  claude)
    Z="${ARMS[0]%h}"
    for pack in k2 "$Z" "$Z" k2; do
      tag="${pack}p$((N + 1))"
      envs="FLASHNEXT_SPLASH_PACK=$pack FLASHNEXT_SPLASH_TAG=1.6.1 FLASHNEXT_CC_PAIR=c,d"
      step "rc2 $pack" "$envs run-arm.sh rc2 131072 --tag $tag" "$envs" "$HERE/scripts/run-arm.sh" rc2 131072 --tag "$tag"
    done ;;
esac
[[ -n "$DRY" ]] || echo "CHAIN-$STAGE: done"
