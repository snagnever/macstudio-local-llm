#!/usr/bin/env bash
# Serve one pack on the rig for the harness sessions that run on the MacBook. Runs ON THE RIG.
# usage: rig-server.sh start <k2|z2|z4> [--print]   stop the user's server, boot Splash 1.6.1 (arm rc2, 131072)
#                                                   with the pack, print BASE_URL= and MODEL_ID=
#        rig-server.sh stop                         stop the bench server and start the user's server again
#        rig-server.sh env                          print BASE_URL= and MODEL_ID= of the running bench server
# The arm stays up because its --exec command waits for logs/server.stop. bash 3.2 (the rig's).
set -uo pipefail
export PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
LOGS="$HERE/logs"; ENVF="$LOGS/server.env"; STOPF="$LOGS/server.stop"; PIDF="$LOGS/server.pid"
RC="$REPO/bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh"
USER_SERVER="$REPO/tools/scripts/serve-flashnext-splash.sh"
PORT=8585
usage() { sed -n '2,7p' "${BASH_SOURCE[0]}" >&2; exit 64; }

port_busy() { lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; }
wait_port_free() { local i; for i in $(seq 1 90); do port_busy || return 0; sleep 2; done; return 1; }
bench_alive() { [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }

stop_bench() {
  if bench_alive; then
    touch "$STOPF"
    local i; for i in $(seq 1 90); do bench_alive || break; sleep 2; done
    bench_alive && kill "$(cat "$PIDF")" 2>/dev/null
  fi
  rm -f "$STOPF" "$ENVF" "$PIDF"
}

stop_listener() {  # whatever listens on the port: the user's server, or a stray one
  local p; p="$(lsof -nP -tiTCP:$PORT -sTCP:LISTEN 2>/dev/null)"
  [[ -n "$p" ]] && kill -INT $p 2>/dev/null
  wait_port_free
}

cmd="${1:-}"; [[ -n "$cmd" ]] || usage; shift
case "$cmd" in
  start)
    pack="${1:-}"; print="${2:-}"
    case "$pack" in k2|z2|z4) ;; *) usage ;; esac
    hold="printf 'BASE_URL=%s\nMODEL_ID=%s\n' \"\$BASE_URL\" \"\$MODEL_ID\" > '$ENVF'; while [ ! -e '$STOPF' ]; do sleep 2; done"
    envs="FLASHNEXT_SPLASH_TAG=1.6.1 FLASHNEXT_SPLASH_PACK=$pack FLASHNEXT_RESULTS_DIR=$LOGS/server-results FLASHNEXT_LOGS_DIR=$LOGS"
    if [[ "$print" == "--print" ]]; then echo "$envs bash $RC rc2 131072 --tag hd-$pack --exec \"$hold\""; exit 0; fi
    mkdir -p "$LOGS/server-results"
    stop_bench
    stop_listener || { echo "rig-server: port $PORT still busy" >&2; exit 1; }
    # shellcheck disable=SC2086
    nohup env $envs bash "$RC" rc2 131072 --tag "hd-$pack" --exec "$hold" < /dev/null > "$LOGS/server-$pack.log" 2>&1 &
    echo $! > "$PIDF"
    for i in $(seq 1 300); do
      [[ -s "$ENVF" ]] && { cat "$ENVF"; exit 0; }
      bench_alive || { echo "rig-server: the arm died at boot; see $LOGS/server-$pack.log" >&2; tail -5 "$LOGS/server-$pack.log" >&2; exit 1; }
      sleep 2
    done
    echo "rig-server: no server after 600 s" >&2; exit 1 ;;
  stop)
    stop_bench
    wait_port_free || stop_listener
    nohup bash "$USER_SERVER" 256k < /dev/null > "$LOGS/user-server.log" 2>&1 &
    for i in $(seq 1 200); do
      curl -fs -m3 "http://127.0.0.1:$PORT/health" >/dev/null && { echo "user server up"; exit 0; }
      sleep 3
    done
    echo "rig-server: USER SERVER DID NOT COME BACK" >&2; exit 1 ;;
  env) [[ -s "$ENVF" ]] && cat "$ENVF" || { echo "rig-server: no bench server" >&2; exit 1; } ;;
  *) usage ;;
esac
