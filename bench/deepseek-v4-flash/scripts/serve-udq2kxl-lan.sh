#!/usr/bin/env bash
# ── RUN THIS ON THE MODEL RIG (macstudio, the 128 GB Mac). ──
# Serve DeepSeek-V4-Flash UD-Q2_K_XL via standalone llama-server, bound to 0.0.0.0 so the
# remote Docker-host Mac can reach it over the LAN for Terminal-Bench.
#
# WHY standalone llama-server (not LM Studio :1234): the `deepseek4` arch's LM Studio-native
# load aborts in the CPU repack path; only `llama-server --no-repack` loads it. So this model
# is NOT on :1234 — it's on :1235, served by this script.
#
# The ONLY difference from the local GO recipe is --host 0.0.0.0 (was 127.0.0.1) so the LAN
# can reach it. All three load-bearing flags kept: 2.24.0 binary (arch), --no-repack (repack
# abort), -np 1 (KV overcommit). Sole-model: 92-98 GB resident — evict everything else first.
#
# Usage:  bash bench/deepseek-v4-flash/scripts/serve-udq2kxl-lan.sh
#   (foreground; leave it running in a terminal for the duration of the remote tbench run)
# First run may trigger a macOS firewall prompt — click "Allow" so incoming LAN connections work.
set -u
BIN=~/.lmstudio/extensions/backends/llama.cpp-mac-arm64-apple-metal-advsimd-2.24.0
M=~/.lmstudio/models/unsloth/DeepSeek-V4-Flash-GGUF/DeepSeek-V4-Flash-UD-Q2_K_XL-00001-of-00003.gguf

[ -f "$M" ] || { echo "ABORT: model shard not found: $M"; exit 1; }

# refuse to start if the LM Studio MLX/GGUF engine or an mlx server is holding memory
pgrep -f mlx_lm.server >/dev/null && { echo "ABORT: mlx_lm.server running — evict it first"; exit 1; }

echo "=== serving deepseek-v4-flash-udq2kxl on 0.0.0.0:1235 (reachable at macstudio.local:1235) ==="
echo "=== leave this running; Ctrl-C to stop after the remote run finishes ==="
cd "$BIN" || { echo "ABORT: llama.cpp 2.24.0 backend dir missing"; exit 1; }
exec ./llama-server -m "$M" -a deepseek-v4-flash-udq2kxl \
  --no-repack -c 32768 -np 1 -ngl 999 --host 0.0.0.0 --port 1235
