#!/usr/bin/env bash
# Capture one screenshot per Agent Build-Off demo arm.
#
#   bench/agent-build-off/scripts/capture-shots.sh [arm ...]
#
# Each arm under demos/<arm>/ is a vite app. The publish workflow builds it with
# the site base (--base=/macstudio-local-llm/demos/build-off/<arm>/), so its
# committed-to-the-site asset URLs only resolve under that prefix. For a local
# capture we rebuild each arm with --base=/ into a throwaway directory outside
# the repo, serve that directory at the server root, and shoot the root URL.
# Nothing under demos/ is written to: demos/<arm>/dist/ is left exactly as the
# workflow (or a previous local build) left it, so `git status` stays clean.
#
# Whatever the app paints after --virtual-time-budget is the artifact. A start
# or menu screen is a valid capture; no clicks are scripted.
#
# Chrome flags: --headless=new --hide-scrollbars --window-size=1280,800
# --virtual-time-budget=10000. Notably NOT --disable-gpu: three.js needs WebGL,
# and headless Chrome's default GPU path renders these scenes correctly on this
# Mac. The SwiftShader fallback (--use-angle=swiftshader
# --enable-unsafe-swiftshader) was not needed — no canvas came out black.
#
# Output: results/shots/<arm>.webp, 1280px wide, cwebp -q 82. Re-runnable:
# it overwrites its own output and rebuilds from source every time.
set -euo pipefail

CAMPAIGN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMOS="$CAMPAIGN/demos"
SHOTS="$CAMPAIGN/results/shots"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Prefer an OS-assigned free port so a stray process squatting on a fixed port
# can't collide with us; PORT can still be forced via the environment.
PORT="${PORT:-$(python3 -c 'import socket;s=socket.socket();s.bind(("",0));print(s.getsockname()[1])')}"
BUDGET_MS="${BUDGET_MS:-10000}"
MAX_BYTES=$((300 * 1024))

ALL_ARMS=(opencode-qwen38 opencode-qwen38-superpowers claude-opus5 codex-astra claude-qwen38)
if [ "$#" -gt 0 ]; then ARMS=("$@"); else ARMS=("${ALL_ARMS[@]}"); fi

[ -x "$CHROME" ] || { echo "no headless Chrome at $CHROME" >&2; exit 1; }
command -v cwebp >/dev/null || { echo "cwebp not on PATH (brew install webp)" >&2; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/build-off-shots.XXXXXX")"
SERVER_PID=""
cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$SHOTS"
fail=0

for arm in "${ARMS[@]}"; do
  src="$DEMOS/$arm"
  [ -d "$src" ] || { echo "!! $arm: no demos/$arm" >&2; fail=1; continue; }
  out="$WORK/$arm"

  echo "== $arm: build"
  if [ ! -d "$src/node_modules" ]; then
    (cd "$src" && npm ci)
  fi
  # --base=/ so the built asset URLs resolve when dist is served at the root.
  # --outDir points outside the repo, so demos/<arm>/dist/ is never touched.
  (cd "$src" && npx vite build --base=/ --outDir "$out" --emptyOutDir) >"$WORK/$arm.build.log" 2>&1 || {
    echo "!! $arm: build failed, see $WORK/$arm.build.log" >&2
    tail -20 "$WORK/$arm.build.log" >&2
    fail=1
    continue
  }

  echo "== $arm: serve + shoot"
  python3 -m http.server "$PORT" --directory "$out" >"$WORK/$arm.serve.log" 2>&1 &
  SERVER_PID=$!
  # Wait for the server to accept connections rather than sleeping blind.
  ready=0
  for _ in $(seq 1 50); do
    if curl -fs -o /dev/null "http://localhost:$PORT/"; then ready=1; break; fi
    sleep 0.2
  done
  if [ "$ready" -ne 1 ]; then
    echo "!! $arm: server never answered at http://localhost:$PORT/ (port $PORT) after 50 tries, see $WORK/$arm.serve.log" >&2
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    SERVER_PID=""
    fail=1
    continue
  fi

  png="$WORK/$arm.png"
  "$CHROME" --headless=new --hide-scrollbars --window-size=1280,800 \
    --virtual-time-budget="$BUDGET_MS" --screenshot="$png" \
    "http://localhost:$PORT/" >"$WORK/$arm.chrome.log" 2>&1 || true

  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""

  if [ ! -s "$png" ]; then
    echo "!! $arm: no screenshot written, see $WORK/$arm.chrome.log" >&2
    fail=1
    continue
  fi

  cwebp -quiet -q 82 -resize 1280 0 "$png" -o "$SHOTS/$arm.webp"
  bytes=$(wc -c <"$SHOTS/$arm.webp" | tr -d ' ')
  if [ "$bytes" -ge "$MAX_BYTES" ]; then
    echo "!! $arm: ${bytes}B >= 300 KB" >&2
    fail=1
  fi
  printf '   %-32s %8s B\n' "$arm.webp" "$bytes"
done

echo
ls -la "$SHOTS"
exit "$fail"
