#!/usr/bin/env bash
# Repeat pairs of real Claude Code sessions (tasks c+d) against one server until the time is over, with a short decode
# probe before the first pair and after each pair. Run it as the --exec of run-arm.sh: it reads BASE_URL and MODEL_ID.
# Results: <out>/cc-soak<tag>p<N>-*.json, req-soak<tag>p<N>-*.jsonl (run-claude-pair.sh) and <out>/soak-<tag>.jsonl.
# usage: agent_soak.sh --hours H --tag TAG [--out DIR]
# Env: CLAUDE_BIN (for the pair); SOAK_PAIR and SOAK_PROBE replace the two commands in tests. bash 3.2 (the rig's).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOURS=""; TAG=""; OUT="$HERE/results"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hours) HOURS="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    *) echo "agent_soak: unknown option: $1" >&2; exit 64 ;;
  esac
done
[[ -n "$HOURS" && -n "$TAG" ]] || { echo "usage: $0 --hours H --tag TAG [--out DIR]" >&2; exit 64; }
PAIR="${SOAK_PAIR:-bash $HERE/../flashnext-concurrency-2026-10/scripts/run-claude-pair.sh}"
PROBE="${SOAK_PROBE:-python3 $HERE/scripts/serving_load.py probe}"
SECONDS_TOTAL="$(python3 -c "print(int(float('$HOURS') * 3600))")"
probe() { $PROBE --base-url "$BASE_URL" --model "$MODEL_ID" --status-url "${BASE_URL%/v1}/status" --status-interval 3600 \
  --out "$OUT/soak-$TAG.jsonl" --label "$1" --reps 3 || echo "agent_soak: probe $1 exit $?" >&2; }
START="$(date +%s)"; N=0
probe pre
while [[ $(( $(date +%s) - START )) -lt "$SECONDS_TOTAL" ]]; do
  N=$((N + 1))
  $PAIR --sessions 2 --pair c,d --proxy 8686 --tag "soak${TAG}p$N" --out "$OUT" || echo "agent_soak: pair $N exit $?" >&2
  probe "pair$N"
done
echo "agent_soak: $N pairs in $(( $(date +%s) - START )) s"
