#!/usr/bin/env bash
# Gate between bands: idle N minutes (default 10), then wait until the GPU is below 50 C (macmon) and free
# memory is at least 82 GB. Refuses to start while a runtime listens on 11234, 8000 or 8080 (stop it first).
# Exit 75 when the GPU or the memory does not settle within 30 minutes.
# usage: idle-gate.sh [--minutes N] [--dry-run]
set -euo pipefail
MIN=10; DRY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MIN="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "usage: $0 [--minutes N] [--dry-run]" >&2; exit 64 ;;
  esac
done
MACMON="${MACMON_BIN:-/opt/homebrew/bin/macmon}"
GPU_MAX="${IDLE_GPU_MAX_C:-50}"; FREE_MIN="${IDLE_FREE_MIN_GB:-82}"
if [[ -n "$DRY" ]]; then
  echo "idle ${MIN} min; then wait gpu < ${GPU_MAX} C and free >= ${FREE_MIN} GB (macmon: $MACMON); ports 11234/8000/8080 must be free"
  exit 0
fi
for p in 11234 8000 8080; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "idle-gate: port $p is in use; stop that server first" >&2; exit 75
  fi
done
echo "idle-gate: idle for $MIN min from $(date '+%T')"
sleep $((MIN * 60))
state() {
  python3 - "$MACMON" <<'PY'
import json, re, subprocess, sys
gpu = json.loads(subprocess.check_output([sys.argv[1], "pipe", "--samples", "1"]).decode())["temp"]["gpu_temp_avg"]
vm = subprocess.check_output(["vm_stat"]).decode()
page = int(re.search(r"page size of (\d+)", vm).group(1))
free = int(re.search(r"Pages free:\s+(\d+)\.", vm).group(1)) * page / 1e9
print(f"{gpu:.1f} {free:.1f}")
PY
}
gpu=""; free=""
for _ in $(seq 1 360); do
  read -r gpu free <<<"$(state)"
  if awk "BEGIN{exit !($gpu < $GPU_MAX && $free >= $FREE_MIN)}"; then
    echo "idle-gate: ready $(date '+%T') gpu=${gpu}C free=${free}GB"; exit 0
  fi
  sleep 5
done
echo "idle-gate: not ready after 30 min (gpu=${gpu}C free=${free}GB)" >&2
exit 75
