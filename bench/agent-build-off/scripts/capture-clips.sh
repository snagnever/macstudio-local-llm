#!/usr/bin/env bash
# Record one short looping clip per Agent Build-Off demo arm.
#
#   bench/agent-build-off/scripts/capture-clips.sh [arm ...]
#
# The video sibling of capture-shots.sh, and it reuses that script's build and
# serve structure verbatim: each arm under demos/<arm>/ is rebuilt with --base=/
# into a throwaway directory outside the repo, served at the server root on an
# OS-assigned free port, and shot at the root URL. Nothing under demos/ is
# written to, so `git status` stays clean.
#
# Headless Chrome cannot write video, so instead of --screenshot we start it
# with --remote-debugging-port and drive Page.startScreencast over the DevTools
# protocol (screencast.mjs, no npm dependencies). Screencast frames arrive at an
# irregular cadence well below 60/s; the driver records each frame's real
# timestamp into an ffmpeg concat playlist and the encode below resamples that
# to true constant 60 fps with -fps_mode cfr -r 60.
#
# The clip has to show the game running, not its menu. All four arms gate their
# world update on a running phase (opencode-qwen38-superpowers is the clearest:
# src/three/GameLoop.tsx steps the world only `if (world.phase === 'running')`),
# so an unattended capture records one still title frame and nothing else. Each
# arm therefore gets its own start input, sent START_AT_MS into the kept footage
# by screencast.mjs over the DevTools Input domain: the clip opens on the title,
# the game starts, and the rest is gameplay. See START_INPUT below for which
# input each arm takes and where that is defined in its source.
#
# Because "it moved" is the whole point, the encode is followed by a motion
# check: mean inter-frame luma difference via tblend=difference + signalstats.
# A clip under MIN_MOTION is deleted and fails the run, so a silently static
# capture cannot ship again.
#
# Output: results/clips/<arm>.mp4, 960x600, H.264 yuv420p, +faststart, no audio,
# CLIP_SECONDS long. Each file must stay under MAX_BYTES (the repo's guideline
# is ~1 MB per tracked artifact), so the encode walks a CRF ladder and takes the
# first rung that fits; if even the last rung is too big it retries at
# FALLBACK_SECONDS before it would give up. Re-runnable: it overwrites its own
# output and rebuilds from source every time.
set -euo pipefail

CAMPAIGN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$CAMPAIGN/scripts"
DEMOS="$CAMPAIGN/demos"
CLIPS="$CAMPAIGN/results/clips"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Prefer OS-assigned free ports so a stray process squatting on a fixed port
# can't collide with us; both can still be forced via the environment.
free_port() { python3 -c 'import socket;s=socket.socket();s.bind(("",0));print(s.getsockname()[1])'; }
PORT="${PORT:-$(free_port)}"
CDP_PORT="${CDP_PORT:-$(free_port)}"

SETTLE_MS="${SETTLE_MS:-2500}"   # warm-up discarded before the first kept frame
CAPTURE_MS="${CAPTURE_MS:-9000}" # captured raw, longer than needed, so we trim
START_AT_MS="${START_AT_MS:-1000}" # title held this long before the start input
# Control presses sent during the run, offsets in ms from the start input. Not
# an attempt to play well or survive: it is there so the clip shows the avatar
# answering the controls and not just the track scrolling. All four arms take
# the same arrow/space vocabulary (each arm's input module maps ArrowLeft /
# ArrowRight to lane changes and Space to jump), so one script serves all.
PLAY_SCRIPT="${PLAY_SCRIPT:-500:ArrowLeft,1100:Space,1700:ArrowRight,2300:ArrowRight,2900:Space,3400:ArrowLeft,3900:Space,4400:ArrowRight,4900:Space}"
CLIP_SECONDS="${CLIP_SECONDS:-6}"
FALLBACK_SECONDS="${FALLBACK_SECONDS:-5}"
WIDTH=960
HEIGHT=600
# 900 kB read the strict way (900,000 B, not 900 KiB), so the tracked files are
# under the guideline however you count. Gameplay costs a lot more bits than the
# idle title screens the first pass encoded, so this is the binding constraint
# for the busier arms now, not a formality.
MAX_BYTES=900000
CRF_LADDER=(23 26 29 32 35 38)
# Mean inter-frame luma difference below this is compression noise, not motion.
MIN_MOTION="${MIN_MOTION:-0.5}"

ALL_ARMS=(opencode-qwen38 opencode-qwen38-superpowers claude-opus5 codex-astra)
if [ "$#" -gt 0 ]; then ARMS=("$@"); else ARMS=("${ALL_ARMS[@]}"); fi

# What starts each game, read out of its own source rather than guessed:
#   opencode-qwen38              src/hooks/useControls.ts maps 'enter' (and 'r')
#                                to startOrRestart(); the title says "press enter".
#   opencode-qwen38-superpowers  src/game/input.ts maps Enter to the 'confirm'
#                                intent, the same thing its PRESS START button fires.
#   claude-opus5                 src/ui/Overlays.tsx renders the START RUN button
#                                as button.primary inside the menu .panel.
#   codex-astra                  src/ui.ts renders <button data-action="start">Start run</button>.
start_input() {
  case "$1" in
    opencode-qwen38) echo 'key:Enter' ;;
    opencode-qwen38-superpowers) echo 'key:Enter' ;;
    claude-opus5) echo 'click:.panel button.primary' ;;
    codex-astra) echo 'click:[data-action="start"]' ;;
    *) echo '' ;;
  esac
}

# Mean inter-frame luma difference of a clip; the number the report quotes.
motion() {
  ffmpeg -v error -i "$1" \
    -vf "tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" \
    -f null - 2>/dev/null |
    awk -F= '/YAVG/{s+=$2;c++} END{if(c) printf "%.4f", s/c; else printf "0.0000"}'
}

[ -x "$CHROME" ] || { echo "no headless Chrome at $CHROME" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH (brew install ffmpeg)" >&2; exit 1; }
command -v node >/dev/null || { echo "node not on PATH" >&2; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/build-off-clips.XXXXXX")"
SERVER_PID=""
CHROME_PID=""
cleanup() {
  [ -n "$CHROME_PID" ] && kill "$CHROME_PID" 2>/dev/null || true
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$CLIPS"
fail=0

# encode <concat-dir> <out.mp4> <seconds> -> echoes "bytes crf", or nothing on failure
#
# The screencast JPEGs are full-range sRGB, so without an explicit in_range=pc
# -> out_range=tv conversion x264 tags the output yuvj420p instead of the plain
# yuv420p browsers expect; the bt709 tags go with that limited-range choice.
encode() {
  local dir="$1" out="$2" secs="$3" crf bytes
  for crf in "${CRF_LADDER[@]}"; do
    ffmpeg -y -loglevel error -f concat -safe 0 -i "$dir/concat.txt" \
      -t "$secs" \
      -vf "scale=$WIDTH:$HEIGHT:flags=lanczos:in_range=pc:out_range=tv,format=yuv420p" \
      -fps_mode cfr -r 60 \
      -c:v libx264 -preset veryslow -crf "$crf" -profile:v high -level 4.0 \
      -pix_fmt yuv420p -color_range tv -colorspace bt709 \
      -color_primaries bt709 -color_trc bt709 \
      -movflags +faststart -an \
      "$out" >"$dir/encode.log" 2>&1 || return 1
    bytes=$(wc -c <"$out" | tr -d ' ')
    if [ "$bytes" -lt "$MAX_BYTES" ]; then
      echo "$bytes $crf"
      return 0
    fi
  done
  return 2
}

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

  echo "== $arm: serve + record"
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

  # Not --disable-gpu: three.js needs WebGL, and headless Chrome's default GPU
  # path renders these scenes correctly on this Mac (same finding as the stills).
  "$CHROME" --headless=new --hide-scrollbars --window-size=1280,800 \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$WORK/$arm.chrome-profile" \
    --no-first-run --no-default-browser-check \
    --autoplay-policy=no-user-gesture-required \
    "http://localhost:$PORT/" >"$WORK/$arm.chrome.log" 2>&1 &
  CHROME_PID=$!

  frames="$WORK/$arm.frames"
  cast_ok=1
  start="$(start_input "$arm")"
  [ -n "$start" ] || echo "!! $arm: no start input defined, capturing the idle title" >&2
  node "$SCRIPTS/screencast.mjs" --port "$CDP_PORT" --out "$frames" \
    --settle "$SETTLE_MS" --capture "$CAPTURE_MS" \
    ${start:+--start "$start" --start-at "$START_AT_MS" --play "$PLAY_SCRIPT"} || cast_ok=0

  kill "$CHROME_PID" 2>/dev/null || true
  wait "$CHROME_PID" 2>/dev/null || true
  CHROME_PID=""
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""

  if [ "$cast_ok" -ne 1 ] || [ ! -s "$frames/concat.txt" ]; then
    echo "!! $arm: screencast produced no frames, see $WORK/$arm.chrome.log" >&2
    fail=1
    continue
  fi

  dest="$CLIPS/$arm.mp4"
  secs="$CLIP_SECONDS"
  if ! result="$(encode "$frames" "$dest" "$secs")"; then
    echo "!! $arm: ${CLIP_SECONDS}s did not fit in $MAX_BYTES B at CRF ${CRF_LADDER[*]}, retrying at ${FALLBACK_SECONDS}s" >&2
    secs="$FALLBACK_SECONDS"
    if ! result="$(encode "$frames" "$dest" "$secs")"; then
      echo "!! $arm: encode failed or never fit the size budget, see $frames/encode.log" >&2
      tail -10 "$frames/encode.log" >&2
      rm -f "$dest"
      fail=1
      continue
    fi
  fi
  bytes="${result%% *}"
  crf="${result##* }"

  # The point of the clip is that the game moves. Prove it, or throw the clip
  # away so the gallery falls back to the arm's still.
  mv="$(motion "$dest")"
  printf '   %-40s %8s B  crf=%s  %ss  motion=%s\n' "$arm.mp4" "$bytes" "$crf" "$secs" "$mv"
  if awk -v m="$mv" -v t="$MIN_MOTION" 'BEGIN{exit !(m < t)}'; then
    echo "!! $arm: motion $mv < $MIN_MOTION — the clip is static, so it is not shipped." >&2
    echo "!! $arm: check that '$start' still starts this build." >&2
    rm -f "$dest"
    fail=1
    continue
  fi
done

echo
for f in "$CLIPS"/*.mp4; do
  [ -e "$f" ] || continue
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames \
    -show_entries format=duration,size -of default=nw=1:nk=1 "$f" |
    paste -sd' ' - | sed "s|^|$(basename "$f") |" | tr -d '\n'
  printf ' motion=%s\n' "$(motion "$f")"
done
exit "$fail"
