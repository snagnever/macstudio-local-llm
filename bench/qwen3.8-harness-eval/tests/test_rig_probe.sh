#!/usr/bin/env bash
# Contract of scripts/rig-probe.sh: it classifies the rig state from two metric
# samples and calls out a half-open client socket — the state where the server
# already ended the request and the client is still waiting on a dead socket.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PROBE="$ROOT/bench/qwen3.8-harness-eval/scripts/rig-probe.sh"

bash -n "$PROBE"

RIG_PROBE_LIB=1 source "$PROBE"

# classify RUNNING PREFILLING GEN_DELTA.
[[ "$(classify 1 1 0)" == PREFILLING ]]
[[ "$(classify 1 0 400)" == GENERATING ]]
[[ "$(classify 1 0 0)" == STALLED ]]
[[ "$(classify 0 0 0)" == IDLE ]]
# A rising decode counter wins over a stale running gauge.
[[ "$(classify 0 0 400)" == GENERATING ]]

# metric reads a Prometheus gauge and stays quiet when it is absent.
SAMPLE='vllm:num_requests_running 1
mlx_serve:requests_prefilling 0
mlx_serve:generation_tokens_live 448038'
[[ "$(metric vllm:num_requests_running <<<"$SAMPLE")" == 1 ]]
[[ "$(metric mlx_serve:generation_tokens_live <<<"$SAMPLE")" == 448038 ]]
[[ -z "$(metric mlx_serve:absent_gauge <<<"$SAMPLE")" ]]

# The failure this script exists for: the client holds a socket the server lost.
grep -q 'HALF-OPEN: 64282' <<<"$(verdict IDLE 64282 '')"
grep -q 'HALF-OPEN: 64282' <<<"$(verdict IDLE '64282
65382' '65382')"
# Same ports on both ends is not a hang.
grep -qv 'HALF-OPEN' <<<"$(verdict IDLE 65382 65382)"
grep -q 'client display is behind' <<<"$(verdict GENERATING 65382 65382)"

# An unknown target is rejected before any network call.
if TARGET=bogus bash "$PROBE" --no-ssh >/dev/null 2>&1; then
  echo "rig-probe.sh accepted TARGET=bogus" >&2
  exit 1
fi

echo "rig-probe: ok"
