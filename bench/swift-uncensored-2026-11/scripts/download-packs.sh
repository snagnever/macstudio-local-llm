#!/usr/bin/env bash
# Download the exact files of the swift-uncensored-2026-11 arms into the HF cache, with the snapshot_download of the
# Splash 1.6.1 Python (the rig has no hf CLI, and the arms start Splash with --offline). k2 is already in the cache.
# Ported from the download-packs.sh of the 2026-11-07 campaign (branch bench/swift15-uncensored-2026-11, rig only).
# usage: download-packs.sh [z0] [z1] [z2] [z3] [--print]   (no arm = z1 z2 z3)
# Check free space first: z0 83.7 GB, z1 95.9 GB, z2 83.7 GB, z3 83.5 GB.
set -euo pipefail
PY="${SPLASH_PY:-$HOME/.local/opt/qwen38/splash-v1.6.1/python/bin/python3}"
PRINT=""; ARMS=()
for a in "$@"; do
  case "$a" in
    --print) PRINT=1 ;;
    z0|z1|z2|z3) ARMS+=("$a") ;;
    *) echo "usage: $0 [z0] [z1] [z2] [z3] [--print]" >&2; exit 64 ;;
  esac
done
[[ ${#ARMS[@]} -gt 0 ]] || ARMS=(z1 z2 z3)
for a in "${ARMS[@]}"; do
  case "$a" in
    z0) REPO=ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF; REV=99bb8f7f95c7aa7b24a36a7786a4f657b30f5d3d
        PATTERNS='["Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-*.gguf", "README.md"]' ;;
    z1) REPO=jackjusko/Swift-1.5-Flash-Next-Heretic-ReverseEngineer; REV=bd3bca068a544d459cf42902bf21a0fac00ec853
        PATTERNS='["IQ4_XS/*.gguf", "README.md"]' ;;
    z2) REPO=huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF; REV=cbc7fba13f1939ac3fa42b18d77ccf43847d74ef
        PATTERNS='["swift-IQ3_S/*.gguf", "README.md"]' ;;
    z3) REPO=SC117/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF; REV=3db919a964b1f0ae0d1000ba7be90b3e38b1f7a3
        PATTERNS='["Swift-Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_S-*.gguf", "README.md"]' ;;
  esac
  CODE="from huggingface_hub import snapshot_download; print(snapshot_download('$REPO', revision='$REV', allow_patterns=$PATTERNS))"
  if [[ -n "$PRINT" ]]; then echo "$a: $PY -c \"$CODE\""; continue; fi
  echo "=== $(date '+%F %T') $a $REPO@$REV"
  "$PY" -c "$CODE"
  echo "=== $(date '+%F %T') $a done"
done
echo "DOWNLOAD: done"
