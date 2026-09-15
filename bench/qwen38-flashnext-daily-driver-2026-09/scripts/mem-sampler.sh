#!/usr/bin/env bash
# Amostra memoria do rig a cada N s em JSONL. Uso:
#   mem-sampler.sh <saida.jsonl> <nome-do-processo-servidor> [intervalo_s]
# Para com SIGTERM/SIGINT. Wired e o que o Metal pina; e o numero do gate de memoria.
set -euo pipefail
OUT="${1:?uso: $0 <saida.jsonl> <server-name> [intervalo]}"
SERVER="${2:?uso: $0 <saida.jsonl> <server-name> [intervalo]}"
INTERVAL="${3:-5}"
trap 'exit 0' TERM INT
mkdir -p "$(dirname "$OUT")"
while :; do
  python3 - "$OUT" "$SERVER" <<'PY'
import json, re, subprocess, sys, time
out, server = sys.argv[1], sys.argv[2]
vm = subprocess.check_output(["vm_stat"]).decode()
page = int(re.search(r"page size of (\d+)", vm).group(1))
def pages(label):
    m = re.search(label + r":\s+(\d+)\.", vm)
    return int(m.group(1)) * page / 1e9 if m else 0.0
swap = subprocess.check_output(["sysctl", "-n", "vm.swapusage"]).decode()
used = re.search(r"used = ([\d.]+)M", swap)
rss = 0.0
try:
    ps = subprocess.check_output(["ps", "-axo", "rss=,comm="]).decode()
    for line in ps.splitlines():
        kb, comm = line.strip().split(None, 1)
        if server in comm:
            rss += int(kb) / 1e6
except Exception:
    pass
rec = {
    "t": int(time.time()),
    "free_gb": round(pages("Pages free"), 2),
    "wired_gb": round(pages("Pages wired down"), 2),
    "compressor_gb": round(pages("Pages occupied by compressor"), 2),
    "swap_used_gb": round(float(used.group(1)) / 1024, 2) if used else 0.0,
    "server_rss_gb": round(rss, 2),
    "server": server,
}
with open(out, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(rec) + "\n")
PY
  sleep "$INTERVAL"
done
