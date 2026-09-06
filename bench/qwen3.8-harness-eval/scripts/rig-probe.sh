#!/usr/bin/env bash
# Answers one question: is the rig generating, prefilling or idle — and is the
# client socket still alive on both ends?
#
# The recurring failure it diagnoses: the TCP path between MacBook and rig
# breaks mid-stream. The server notices on the next write and ends the request
# with [client_disconnect]; the client is only reading, has no read timeout,
# and waits forever showing "prefill".
#
# Inputs (env):
#   TARGET     rig target: 27b | fn (default fn)
#   RIG_HOST   rig hostname on the tailnet (default mac-studio)
#   RIG_PORT   runtime port (default from TARGET)
#   RIG_USER   ssh user on the rig (default vitor)
#   WINDOW     sampling window in seconds (default 6)
#
# Flags: --no-ssh skips the rig-side checks (log growth, server sockets).
set -euo pipefail

TARGET="${TARGET:-fn}"
case "$TARGET" in
  fn)  DEFAULT_PORT=11234 ;;
  27b) DEFAULT_PORT=8484 ;;
  *) echo "TARGET must be 27b or fn (got '$TARGET')" >&2; exit 64 ;;
esac
RIG_HOST="${RIG_HOST:-mac-studio}"
RIG_PORT="${RIG_PORT:-$DEFAULT_PORT}"
RIG_USER="${RIG_USER:-vitor}"
WINDOW="${WINDOW:-6}"
USE_SSH=1
[[ "${1:-}" == "--no-ssh" ]] && USE_SSH=0

# metric NAME <<< TEXT: value of a Prometheus gauge, empty when absent.
metric() {
  awk -v n="$1" '$1 == n { print $2; exit }'
}

# classify RUNNING PREFILLING GEN_DELTA: one word for the server state.
classify() {
  local running="${1:-0}" prefilling="${2:-0}" gen_delta="${3:-0}"
  if [[ "$prefilling" -gt 0 ]]; then echo PREFILLING
  elif [[ "$gen_delta" -gt 0 ]]; then echo GENERATING
  elif [[ "$running" -gt 0 ]]; then echo STALLED
  else echo IDLE
  fi
}

# verdict STATE CLIENT_PORTS SERVER_PORTS: the line that answers the question.
verdict() {
  local state="$1" client="$2" server="$3" half=""
  local p
  for p in $client; do
    grep -qx "$p" <<<"$server" || half="$half $p"
  done
  case "$state" in
    GENERATING|PREFILLING) echo "server is working — the client display is behind" ;;
    STALLED) echo "server holds the request but emitted no token in the window — watch it or raise --timeout" ;;
    IDLE)
      if [[ -n "$half" ]]; then
        echo "HALF-OPEN:$half — the server already dropped these; the client will wait forever. Cancel and resend."
      elif [[ -n "$client" ]]; then
        echo "server idle with a live socket — the client is between requests"
      else
        echo "server idle, no client socket"
      fi
      ;;
  esac
}

[[ "${RIG_PROBE_LIB:-0}" == 1 ]] && return 0

RIG_LOG="\$HOME/.mlx-serve/logs/mlx-serve-$RIG_PORT.log"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Rig-side sample runs in parallel with the local one, over the same window.
if [[ "$USE_SSH" -eq 1 ]]; then
  ssh -o ConnectTimeout=8 -o BatchMode=yes "$RIG_USER@$RIG_HOST" "
    wc -l < $RIG_LOG 2>/dev/null || echo 0
    netstat -an | awk '/\.$RIG_PORT / && /ESTABLISHED/ { n = split(\$5, a, \".\"); print a[n] }'
    echo ---
    sleep $WINDOW
    wc -l < $RIG_LOG 2>/dev/null || echo 0
    grep -a 'tokens streamed' $RIG_LOG 2>/dev/null | tail -1
  " >"$TMP/rig" 2>"$TMP/rig.err" &
  RIG_PID=$!
fi

M1="$(curl -s -m 10 "http://$RIG_HOST:$RIG_PORT/metrics" || true)"
sleep "$WINDOW"
M2="$(curl -s -m 10 "http://$RIG_HOST:$RIG_PORT/metrics" || true)"

RUNNING="$(metric vllm:num_requests_running <<<"$M2")"
PREFILLING="$(metric mlx_serve:requests_prefilling <<<"$M2")"
CANCELLED="$(metric vllm:request_cancelled_total <<<"$M2")"
G1="$(metric mlx_serve:generation_tokens_live <<<"$M1")"
G2="$(metric mlx_serve:generation_tokens_live <<<"$M2")"
P1="$(metric mlx_serve:prefill_tokens_live <<<"$M1")"
P2="$(metric mlx_serve:prefill_tokens_live <<<"$M2")"

if [[ -z "$G2" ]]; then
  echo "metrics  unavailable at http://$RIG_HOST:$RIG_PORT/metrics (runtime down, or started without --metrics)"
  RUNNING=0 PREFILLING=0 GEN_DELTA=0
else
  GEN_DELTA="$(awk -v a="${G1:-0}" -v b="$G2" 'BEGIN { d = b - a; print (d > 0 ? int(d) : 0) }')"
  PRE_DELTA="$(awk -v a="${P1:-0}" -v b="${P2:-0}" 'BEGIN { d = b - a; print (d > 0 ? int(d) : 0) }')"
fi

CLIENT_PORTS="$(lsof -nP -iTCP -sTCP:ESTABLISHED 2>/dev/null \
  | awk -v p=":$RIG_PORT" '$0 ~ p { n = split($9, a, ":"); sub(/->.*/, "", a[2]); print a[2] }' | sort -u)"

SERVER_PORTS=""
if [[ "$USE_SSH" -eq 1 ]]; then
  wait "$RIG_PID" || true
  SERVER_PORTS="$(sed -n '2,/^---$/p' "$TMP/rig" | grep -v '^---$' | sort -u)"
  LOG_BEFORE="$(sed -n '1p' "$TMP/rig")"
  LOG_AFTER="$(sed -n '/^---$/{n;p;}' "$TMP/rig")"
  LAST_REQ="$(tail -1 "$TMP/rig")"
fi

STATE="$(classify "${RUNNING:-0}" "${PREFILLING:-0}" "${GEN_DELTA:-0}")"

echo "endpoint  $RIG_HOST:$RIG_PORT ($TARGET)"
printf 'state     %s   running=%s prefilling=%s cancelled_total=%s\n' \
  "$STATE" "${RUNNING:-?}" "${PREFILLING:-?}" "${CANCELLED:-?}"
if [[ -n "${GEN_DELTA:-}" ]]; then
  printf 'rate      decode %s tok/s   prefill %s tok/s   (over %ss)\n' \
    "$(( GEN_DELTA / WINDOW ))" "$(( ${PRE_DELTA:-0} / WINDOW ))" "$WINDOW"
fi
printf 'sockets   client [%s]  server [%s]\n' "$(echo $CLIENT_PORTS)" "$(echo $SERVER_PORTS)"
if [[ "$USE_SSH" -eq 1 ]]; then
  printf 'log       +%s lines in %ss\n' "$(( ${LOG_AFTER:-0} - ${LOG_BEFORE:-0} ))" "$WINDOW"
  printf 'last      %s\n' "${LAST_REQ:0:160}"
fi
echo "verdict   $(verdict "$STATE" "$CLIENT_PORTS" "$SERVER_PORTS")"
