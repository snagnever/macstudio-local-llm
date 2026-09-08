#!/usr/bin/env bash
# Capture the five iterations of each layout-skill-bench arm.
#
#   bench/layout-skill-bench/scripts/capture-shots.sh [arm ...]
#
# The three arms ship in three different shapes, so each is staged into a
# throwaway directory outside the repo and served at the server root:
#
#   design-skill  static, one dir per iteration: demos/design-skill/<n>/index.html
#                 -> copied as-is; shot at /<n>/
#   taste2        static, one file per iteration: demos/taste2/pages/<n>.html
#                 (the run served these from a small Node server; publish adds
#                 an index and rewrites the extensionless links)
#                 -> copied as-is; shot at /<n>.html
#   taste-skill   a vite + React app whose five iterations are client-side
#                 history-API routes /1../5 (src/App.tsx ITERATIONS), which is
#                 why the site is published at demos/layout/taste-skill/<n>.
#                 -> built with --base=/ (so the publish-time
#                    taste-skill.basepath.patch, which only exists to rebase
#                    those routes under the site prefix, is NOT applied and the
#                    tracked src/App.tsx is never edited), then dist/index.html
#                    is copied to <n>/index.html as a static stand-in for the
#                    server history fallback; shot at /<n>/, where normalize()
#                    strips the trailing slash and matches the route.
#
# Nothing under demos/ is written to — no patch is applied, no dist/ is built
# in place — so `git status` stays clean under demos/.
#
# Chrome flags: --headless=new --hide-scrollbars --window-size=1280,800
# --virtual-time-budget=10000, no --disable-gpu (same set as the build-off
# script; the SwiftShader fallback was not needed for any arm). The capture is
# the 1280x800 viewport, i.e. the top of each page, not the full scroll height.
#
# Output: results/shots/<arm>-<n>.webp, 1280px wide, cwebp -q 82. Re-runnable.
set -euo pipefail

CAMPAIGN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMOS="$CAMPAIGN/demos"
SHOTS="$CAMPAIGN/results/shots"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT="${PORT:-8732}"
BUDGET_MS="${BUDGET_MS:-10000}"
MAX_BYTES=$((300 * 1024))

ALL_ARMS=(design-skill taste-skill taste2)
if [ "$#" -gt 0 ]; then ARMS=("$@"); else ARMS=("${ALL_ARMS[@]}"); fi

[ -x "$CHROME" ] || { echo "no headless Chrome at $CHROME" >&2; exit 1; }
command -v cwebp >/dev/null || { echo "cwebp not on PATH (brew install webp)" >&2; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/layout-shots.XXXXXX")"
SERVER_PID=""
cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$SHOTS"
fail=0

# stage <arm> <root>: fill $root with a statically servable copy of the arm and
# echo the five URL paths (one per line, iterations 1..5).
stage() {
  local arm="$1" root="$2" n
  case "$arm" in
    design-skill)
      for n in 1 2 3 4 5; do
        mkdir -p "$root/$n"
        cp "$DEMOS/design-skill/$n/index.html" "$root/$n/index.html"
        echo "/$n/"
      done
      ;;
    taste2)
      for n in 1 2 3 4 5; do
        cp "$DEMOS/taste2/pages/$n.html" "$root/$n.html"
        echo "/$n.html"
      done
      ;;
    taste-skill)
      local src="$DEMOS/taste-skill"
      if [ ! -d "$src/node_modules" ]; then (cd "$src" && npm ci) >&2; fi
      (cd "$src" && npx vite build --base=/ --outDir "$root" --emptyOutDir) >"$WORK/taste-skill.build.log" 2>&1
      for n in 1 2 3 4 5; do
        mkdir -p "$root/$n"
        cp "$root/index.html" "$root/$n/index.html"
        echo "/$n/"
      done
      ;;
    *)
      echo "unknown arm: $arm" >&2
      return 1
      ;;
  esac
}

for arm in "${ARMS[@]}"; do
  echo "== $arm: stage"
  root="$WORK/$arm"
  mkdir -p "$root"
  if ! paths=$(stage "$arm" "$root"); then
    echo "!! $arm: staging failed" >&2
    [ -f "$WORK/$arm.build.log" ] && tail -20 "$WORK/$arm.build.log" >&2
    fail=1
    continue
  fi

  echo "== $arm: serve + shoot"
  python3 -m http.server "$PORT" --directory "$root" >"$WORK/$arm.serve.log" 2>&1 &
  SERVER_PID=$!
  for _ in $(seq 1 50); do
    if curl -fs -o /dev/null "http://localhost:$PORT/"; then break; fi
    sleep 0.2
  done

  n=0
  while IFS= read -r path; do
    n=$((n + 1))
    png="$WORK/$arm-$n.png"
    "$CHROME" --headless=new --hide-scrollbars --window-size=1280,800 \
      --virtual-time-budget="$BUDGET_MS" --screenshot="$png" \
      "http://localhost:$PORT$path" >"$WORK/$arm-$n.chrome.log" 2>&1 || true
    if [ ! -s "$png" ]; then
      echo "!! $arm-$n: no screenshot written ($path), see $WORK/$arm-$n.chrome.log" >&2
      fail=1
      continue
    fi
    cwebp -quiet -q 82 -resize 1280 0 "$png" -o "$SHOTS/$arm-$n.webp"
    bytes=$(wc -c <"$SHOTS/$arm-$n.webp" | tr -d ' ')
    if [ "$bytes" -ge "$MAX_BYTES" ]; then
      echo "!! $arm-$n: ${bytes}B >= 300 KB" >&2
      fail=1
    fi
    printf '   %-24s %-12s %8s B\n' "$arm-$n.webp" "$path" "$bytes"
  done <<<"$paths"

  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
done

echo
ls -la "$SHOTS"
exit "$fail"
