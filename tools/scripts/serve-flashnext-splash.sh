#!/usr/bin/env bash
# Start Qwen3.8-Flash-Next on Splash 1.6.1 (Inco AI): Swift 1.5 GGUF IQ4_XS (ukisai 0142554) with the DFlash2 draft
# Splash selects, --verify-rows auto, KV int8 (the Splash default). This is the k2a arm of
# bench/splash-longctx-2026-10; it does not replace the daily driver (serve-flashnext-daily-driver.sh).
# Release 1.6.1 since 2026-11-12 (bench/splash161-2026-11): T_turno 1.000-1.017 x 1.5.0 at 32K-256K, two 256K
#   sessions 1.035 x 1.5.0, Claude Code pair wall 0.97 x, no stall under --max-memory 64G, same quality, 4 h soak
#   stable. PLE table mode is auto (the 1.6.1 default, no flag): the 27 GB table stays on the SSD with a 237 MiB
#   row cache, so the wired peak drops 22-29 GB. Rollback: FLASHNEXT_SPLASH_BIN=$HOME/.local/opt/qwen38/splash-v1.5.0/bin/splash
# Profiles (every one passed speed, memory and quality on Splash 1.4.0 in
#   bench/splash-longctx-2026-10/results/params-512k-1m.md):
#   256k (default) 262144 tokens, native context. T_turno 6.3 s at 256K on 1.6.1, decode ~109 tok/s.
#   512k           524288 tokens; Splash turns YaRN on by itself. T_turno 6.7 s, folga 10.1 GB, longctx 100% (1.4.0;
#                  not measured on 1.6.1).
#   1m             1000000 tokens. On 1.6.1 the whole window stays resident: T_turno 7.0 s, decode 102 tok/s,
#                  needles 5/5 (1 rep); a cold 1M prompt takes ~25 min. HumanEval sat 1 question under the G1
#                  margin on 1.4.0 (run noise).
# YaRN above 262144 changes answers to short prompts too: use 512k or 1m only when the context needs it.
# Cache: Splash keeps the hybrid state only where a request ends. Editing or branching a long history before its
#   last saved point (a compaction, a retried turn) re-prefills the whole prompt (incoai/splash#387, #361).
# Concurrency (1.6.1): decode runs in one batch, prefill one request at a time, so a second session's prefill
#   stalls the first one's decode. Two 256K sessions: worst stream 16.6 s vs 16.1 s on 1.5.0; no memory wait.
# Clients must send frequency_penalty 0, as with the daily driver.
# Overrides: FLASHNEXT_SPLASH_BIN, FLASHNEXT_SPLASH_PORT (default 8585), FLASHNEXT_SPLASH_HOST (default 0.0.0.0).
#            Add --print to show the command without starting.
set -euo pipefail

PROFILE="256k"
PRINT=""
for arg in "$@"; do
  case "$arg" in
    256k|512k|1m) PROFILE="$arg" ;;
    --print) PRINT=1 ;;
    *) echo "usage: $0 [256k|512k|1m] [--print]" >&2; exit 64 ;;
  esac
done

BIN="${FLASHNEXT_SPLASH_BIN:-$HOME/.local/opt/qwen38/splash-v1.6.1/bin/splash}"
HOST="${FLASHNEXT_SPLASH_HOST:-0.0.0.0}"
PORT="${FLASHNEXT_SPLASH_PORT:-8585}"
case "$PROFILE" in
  256k) CTX=262144 ;;
  512k) CTX=524288 ;;
  1m) CTX=1000000 ;;
esac

COMMAND=(
  "$BIN" serve
  --model ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF:IQ4_XS
  --host "$HOST" --port "$PORT"
  --max-context "$CTX"
  --revision 0142554c963a8653912c0c8283f05f13f63653f3
  --idle-release off --language-only --no-webui --offline
  --verify-rows auto
)

if [[ -n "$PRINT" ]]; then
  echo "${COMMAND[*]}"
  exit 0
fi

[[ -x "$BIN" ]] || { echo "splash binary not found: $BIN" >&2; exit 66; }
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $PORT is already in use; stop the running server first" >&2
  exit 69
fi
echo "Flash-Next on Splash ($PROFILE) on http://$HOST:$PORT/v1" >&2
exec "${COMMAND[@]}"
