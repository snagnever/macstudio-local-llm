#!/usr/bin/env bash
# Run N cache_probe.py streams in parallel against one server (BASE_URL, MODEL_ID from run-candidate.sh --exec),
# one JSONL per stream, plus an optional auxiliary load generator (aux_load.py) while the probes run.
# Odd streams use the audit_retrieval fixture, even streams the code fixture; streams 3+ add a prompt salt
# so they never share a prefix with streams 1 and 2. Exit status is non-zero if any probe stream failed.
# bash 3.2 (the rig's): no associative arrays, no mapfile.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PROBE="$REPO/bench/qwen3.8-prefix-cache/scripts/cache_probe.py"
PY="${PARALLEL_PYTHON:-python3}"

usage() { echo "usage: $0 --streams N [--aux] --context CTX [--contexts C1,C2,...] --repeat R --arm ARM --tag TAG --out DIR [--temperature T] [--reasoning-effort E] [--runtime-revision REV] [--model-revision SHA] [--dry-run]" >&2; exit 64; }

STREAMS=""; AUX=""; CTX=""; CONTEXTS=""; REPEAT=""; ARM=""; TAG=""; OUT=""; DRY=""
TEMP=1.0; EFFORT=xhigh; RUNTIME_REV=v26.10.1; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --streams) STREAMS="$2"; shift 2 ;;
    --aux) AUX=1; shift ;;
    --context) CTX="$2"; shift 2 ;;
    --contexts) CONTEXTS="$2"; shift 2 ;;
    --repeat) REPEAT="$2"; shift 2 ;;
    --arm) ARM="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --temperature) TEMP="$2"; shift 2 ;;
    --reasoning-effort) EFFORT="$2"; shift 2 ;;
    --runtime-revision) RUNTIME_REV="$2"; shift 2 ;;
    --model-revision) MODEL_REV="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) echo "run-parallel-probes: unknown option: $1" >&2; usage ;;
  esac
done
[[ -n "$STREAMS" && -n "$REPEAT" && -n "$ARM" && -n "$TAG" && -n "$OUT" ]] || usage
[[ -n "$CTX" || -n "$CONTEXTS" ]] || usage
[[ -n "$CTX" ]] || CTX="${CONTEXTS%%,*}"

# One context per stream: --contexts wins over --context.
CTXS=()
if [[ -n "$CONTEXTS" ]]; then
  IFS=, read -r -a CTXS <<<"$CONTEXTS"
  if [[ "${#CTXS[@]}" -ne "$STREAMS" ]]; then
    echo "run-parallel-probes: --contexts has ${#CTXS[@]} values for $STREAMS streams" >&2; exit 64
  fi
else
  for ((k = 0; k < STREAMS; k++)); do CTXS+=("$CTX"); done
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:11234/v1}"
MODEL_ID="${MODEL_ID:-MODEL_ID}"
RUNNING="$OUT/${ARM}-${CTX}-${TAG}.running"
LOGDIR="${FLASHNEXT_LOGS_DIR:-$OUT}"  # per-stream stdout/stderr stays out of results/ when run-arm.sh sets it
AUX_OUT="$OUT/${ARM}-${CTX}-${TAG}-aux.jsonl"

# Each builder fills the global CMD array; the caller prints it (--dry-run) or runs it (no eval: bash 3.2
# turns the exit status of a backgrounded eval into 1).
probe_cmd() {  # $1 = stream index (1-based)
  local k="$1" ctx="${CTXS[$(($1 - 1))]}" class=audit_retrieval salt=""
  (( k % 2 == 0 )) && class=code
  (( k >= 3 )) && salt="s$k"
  CMD=("$PY" "$PROBE" --base-url "$BASE_URL" --model "$MODEL_ID" --api-model "$MODEL_ID"
    --runtime mlx-serve --runtime-revision "$RUNTIME_REV" --model-revision "$MODEL_REV"
    --arm "$ARM" --session-id "${ARM}-${TAG}-s${k}" --context "$ctx" --content-class "$class"
    --repeat "$REPEAT" --concurrency "$STREAMS"
    --temperature "$TEMP" --top-p 0.95 --top-k 20 --reasoning-effort "$EFFORT")
  if [[ "$REPEAT" -gt 1 ]]; then CMD+=(--scenario-repeats middle_mutation=1); fi
  if [[ -n "$salt" ]]; then CMD+=(--prompt-salt "$salt"); fi
  CMD+=(--output "$OUT/${ARM}-${ctx}-${TAG}-s${k}.jsonl" --cache-enabled --mtp-enabled)
}

aux_cmd() {
  CMD=("$PY" "$HERE/aux_load.py" --base-url "$BASE_URL" --model "$MODEL_ID" --period 20
    --duration-file "$RUNNING" --output "$AUX_OUT")
}

if [[ -n "$DRY" ]]; then
  for ((k = 1; k <= STREAMS; k++)); do probe_cmd "$k"; printf '%q ' "${CMD[@]}"; echo; done
  if [[ -n "$AUX" ]]; then aux_cmd; printf '%q ' "${CMD[@]}"; echo; fi
  exit 0
fi

mkdir -p "$OUT" "$LOGDIR"
# cache_probe.py appends to --output: rotate a stale file so a retry never mixes two runs.
for ((k = 1; k <= STREAMS; k++)); do
  f="$OUT/${ARM}-${CTXS[$((k - 1))]}-${TAG}-s${k}.jsonl"
  [[ -s "$f" ]] && mv "$f" "$f.bak.$(date -u +%Y%m%dT%H%M%SZ)"
done
[[ -n "$AUX" && -s "$AUX_OUT" ]] && mv "$AUX_OUT" "$AUX_OUT.bak.$(date -u +%Y%m%dT%H%M%SZ)"

AUX_PID=""; PIDS=()
cleanup() {
  rm -f "$RUNNING"
  for p in "${PIDS[@]:-}"; do [[ -n "$p" ]] && kill "$p" 2>/dev/null || true; done
  if [[ -n "$AUX_PID" ]]; then
    # aux_load.py exits after its current call once the duration file is gone; kill it if it lingers.
    for _ in $(seq 1 90); do kill -0 "$AUX_PID" 2>/dev/null || break; sleep 1; done
    kill "$AUX_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

: > "$RUNNING"
if [[ -n "$AUX" ]]; then
  : > "$AUX_OUT"  # an empty file means the generator ran and wrote nothing; summarize fails on that
  aux_cmd; "${CMD[@]}" & AUX_PID=$!
fi
for ((k = 1; k <= STREAMS; k++)); do
  probe_cmd "$k"; "${CMD[@]}" > "$LOGDIR/${ARM}-${CTXS[$((k - 1))]}-${TAG}-s${k}.log" 2>&1 & PIDS+=($!)
done

FAILED=0
for ((k = 1; k <= STREAMS; k++)); do
  rc=0; wait "${PIDS[$((k - 1))]}" || rc=$?
  PIDS[$((k - 1))]=""
  echo "    stream s$k exit $rc"
  [[ "$rc" -ne 0 ]] && FAILED=1
done
rm -f "$RUNNING"
if [[ -n "$AUX_PID" ]]; then
  # The generator exits after its current call (at most its 300 s timeout) once the duration file is gone.
  rc=0; wait "$AUX_PID" || rc=$?
  AUX_PID=""
  echo "    aux exit $rc"
  [[ "$rc" -ne 0 ]] && FAILED=1
fi
exit "$FAILED"
