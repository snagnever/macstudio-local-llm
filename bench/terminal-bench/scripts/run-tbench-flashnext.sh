#!/usr/bin/env bash
# Terminal-Bench 2.0 (89 tarefas, terminus-2) no driver Flash-Next servido pelo launcher diário.
# uso: run-tbench-flashnext.sh <n2|w1> [ak=valor ...]
# Os kwargs viram --ak do harbor (valor em JSON). Perfil t1 (sampling do vendor) no terminus-2 0.8.0:
#   reasoning_effort=xhigh temperature=1.0 interleaved_thinking=true \
#   'llm_call_kwargs={"top_p":0.95,"extra_body":{"top_k":20,"min_p":0,"presence_penalty":0,"repetition_penalty":1.0}}'
set -u
ARM="${1:?uso: $0 <n2|w1> [kwarg=valor ...]}"; shift
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"
ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache"
case "$ARM" in
  n2) MODEL="$ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a" ;;
  w1) MODEL="$ROOT/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0" ;;
  *) echo "braço fora do plano: $ARM" >&2; exit 64 ;;
esac
AK=(); for kv in "$@"; do AK+=(--ak "$kv"); done
LOGDIR="$REPO/bench/terminal-bench/logs"; mkdir -p "$LOGDIR/tbench-runs"
export OPENAI_API_BASE="http://127.0.0.1:11234/v1" OPENAI_API_KEY="local" DOCKER_DEFAULT_PLATFORM=linux/amd64
export PATH="$HOME/.local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/local/bin:$PATH"

FLASHNEXT_MODEL="$MODEL" nohup bash tools/scripts/serve-flashnext-daily-driver.sh >"$LOGDIR/tbench-flashnext-$ARM-server.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null; kill $(lsof -nP -tiTCP:11234 -sTCP:LISTEN) 2>/dev/null' EXIT
for _ in $(seq 1 200); do curl -fsS --max-time 3 "$OPENAI_API_BASE/models" >/dev/null 2>&1 && break; sleep 3; done
MODEL_ID="$(curl -fsS "$OPENAI_API_BASE/models" | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["id"])')"
echo "=== start $(date -Iseconds) arm=$ARM model=$MODEL_ID kwargs=$* ===" >> "$LOGDIR/tbench-flashnext-$ARM-driver.log"

harbor run \
  --dataset terminal-bench/terminal-bench-2 \
  --agent terminus-2 \
  --model "openai/$MODEL_ID" \
  --env docker -n 1 -y --quiet \
  --agent-timeout-multiplier 0.5 \
  ${AK[@]+"${AK[@]}"} \
  --jobs-dir bench/terminal-bench/logs/tbench-runs \
  --job-name "flashnext-$ARM" \
  > "$LOGDIR/tbench-flashnext-$ARM.log" 2>&1
RC=$?
echo "=== done $(date -Iseconds) rc=$RC ===" >> "$LOGDIR/tbench-flashnext-$ARM-driver.log"
exit $RC
