#!/usr/bin/env bash
# Run a queue of splash-concurrency-2026-10 arms one after the other through run-arm.sh (one server at a time), with 120 s between arms.
# Each spec is "arm:ctx:reps:tag" or "arm:ctx:reps:tag:yarn". The whole queue is validated before the first
# arm starts. A failing arm does not stop the queue; its exit code is printed.
# usage: run-seq.sh [--dry-run] <spec> [<spec> ...]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=""
if [[ "${1:-}" == --dry-run ]]; then DRY=1; shift; fi
if [[ $# -eq 0 ]]; then echo "usage: $0 [--dry-run] arm:ctx:reps:tag[:yarn] ..." >&2; exit 64; fi
for spec in "$@"; do
  [[ "$spec" =~ ^[A-Za-z0-9]+:[0-9]+:[0-9]+:[a-z0-9]+(:[0-9]+\.[0-9]+)?$ ]] \
    || { echo "run-seq: bad spec: $spec" >&2; exit 64; }
done
n=0
for spec in "$@"; do
  n=$((n + 1))
  IFS=: read -r arm ctx reps tag yarn <<<"$spec"
  args=("$arm" "$ctx" --repeat "$reps" --tag "$tag")
  [[ -n "$yarn" ]] && args+=(--yarn "$yarn")
  if [[ -n "$DRY" ]]; then echo "bash run-arm.sh ${args[*]}"; continue; fi
  echo "=== $(date '+%F %T') start $arm@$ctx x$reps tag=$tag${yarn:+ yarn=$yarn}"
  rc=0; bash "$HERE/scripts/run-arm.sh" "${args[@]}" || rc=$?
  echo "=== $(date '+%F %T') exit[$arm@$ctx]=$rc"
  if [[ $n -lt $# ]]; then sleep 120; fi
done
