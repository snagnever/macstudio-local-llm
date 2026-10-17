#!/usr/bin/env bash
# Gate between bands: idle N minutes (default 10), then wait until the GPU is below 50 C (macmon) and free
# memory is at least 82 GB. Refuses to start while a runtime listens on 11234 (mlx-serve), 8000 (oMLX/MTPLX), 8080 (llama.cpp),
# 8484 (mlx-dspark) or 8585 (Splash); stop it first.
# Exit 75 when the GPU or the memory does not settle within 30 minutes.
# usage: idle-gate.sh [--minutes N] [--dry-run] [--print-ports]
set -euo pipefail
MIN=10; DRY=""
PORTS=(11234 8000 8080 8484 8585)   # mlx-serve, oMLX/MTPLX, llama.cpp, mlx-dspark, Splash
while [[ $# -gt 0 ]]; do
  case "$1" in
    --minutes) MIN="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --print-ports) echo "${PORTS[*]}"; exit 0 ;;
    *) echo "usage: $0 [--minutes N] [--dry-run] [--print-ports]" >&2; exit 64 ;;
  esac
done
MACMON="${MACMON_BIN:-/opt/homebrew/bin/macmon}"
GPU_MAX="${IDLE_GPU_MAX_C:-50}"; FREE_MIN="${IDLE_FREE_MIN_GB:-82}"
if [[ -n "$DRY" ]]; then
  echo "idle ${MIN} min; then wait gpu < ${GPU_MAX} C and free >= ${FREE_MIN} GB (macmon: $MACMON); ports ${PORTS[*]} must be free"
  exit 0
fi
for p in "${PORTS[@]}"; do
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
# Free = memory not held by the kernel or by processes: total - wired - anonymous - compressor.
# File-backed pages (model weights read by earlier runs) are reclaimable; after large downloads and
# runs they sit in speculative or inactive pages and "Pages free" alone stays far below the threshold.
def pg(k):
    return int(re.search(rf"{k}:\s+(\d+)\.", vm).group(1))
total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode())
held = pg("Pages wired down") + pg("Anonymous pages") + pg("Pages occupied by compressor")
free = (total - held * page) / 1e9
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
