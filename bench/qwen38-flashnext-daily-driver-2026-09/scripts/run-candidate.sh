#!/usr/bin/env bash
# Driver unico da campanha flashnext-daily-driver: sobe UM candidato, roda o cache_probe com o
# perfil do vendor, amostra memoria e derruba o servidor. Um candidato por vez.
#   c1 = ddalcu mixed-4/8 @ mlx-serve 26.9.2      c2 = Jundot oQ4e @ oMLX 0.6.4
#   c3 = Jundot oQ4e @ oMLX 0.7.0.dev2            c4 = MTPLX Optimized-Speed @ MTPLX 2.11.2
#   n1/n2/n2p = campanha flashnext-updates-2026-10 (mlx-serve 26.10.1; n2 = pack iQ-MLX-4.7bpw; n2p = n2 + --ple-gpu)
#   engine-updates-2026-10: m1/m1b = MTPLX 2.12.2 (m1b: limite 96G), o1 = oMLX 0.7.0, d1 = ds4 upstream;
#   r27 = 27B @ mlx-serve 26.10.1 + DFlash2, m27 = MTPLX 2.12.2, o27 = oMLX 0.7.0, s27 = mlx-dspark 0.20.3
#   Etapa F (um knob por braço): m1t/m1h/m1th = m1 + pin TTL 0 / header de sessão / os dois;
#   m1p/m1hp = m1 + prime com 64 tokens / + header de sessão;
#   m27f = m27 + knob de ENGINE_M27F; r27b = r27 + --draft-block-size 5; s27g = s27 + --no-memory-guard;
#   s27r = s27 + --prefix-cache-rungs 1024
set -euo pipefail

CAND="${1:?uso: $0 <c1|c2|c3|c4|u1|u2|n1|n2|n2p|m1|m1b|m1t|m1h|m1th|m1p|m1hp|o1|d1|r27|r27b|m27|m27f|o27|s27|s27g|s27r> <ctx> [--scenarios a,b] [--repeat N] [--temperature T] [--tag X] [--yarn F] [--generation-mode M] [--print]}"
CTX="${2:?ctx obrigatorio}"; shift 2
SCENARIOS=""; REPEAT=1; TEMP=1.0; TAG=""; YARN=""; GENMODE=""; PRINT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenarios) SCENARIOS="$2"; shift 2 ;;
    --repeat) REPEAT="$2"; shift 2 ;;
    --temperature) TEMP="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --yarn) YARN="$2"; shift 2 ;;
    --generation-mode) GENMODE="$2"; shift 2 ;;
    --print) PRINT=1; shift ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
HERE="$REPO/bench/qwen38-flashnext-daily-driver-2026-09"
# Outra campanha pode reusar este driver apontando a saída para o próprio diretório.
RESULTS="${FLASHNEXT_RESULTS_DIR:-$HERE/results}"; LOGS="${FLASHNEXT_LOGS_DIR:-$HERE/logs}"
MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache"
DDALCU="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
OQ4E="$MODEL_ROOT/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
MTPLXPACK="$MODEL_ROOT/Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"
# Etapa U: variantes uncensored, mesmo runtime/layout dos candidatos de referencia.
U1DIR="$MODEL_ROOT/ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit-9ebf9993b1eaec96aec938bf883601b51a90393b"
U2DIR="$MODEL_ROOT/latent-variable-Qwen3.8-Flash-Next-heretic-2-oQ4e-mtp-65b0cd6"
# Campanha flashnext-updates-2026-10: pack calibrado (mesmo layout do DDALCU) e runtime 26.10.1.
IQDIR="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
MLXSERVE_26101="$HOME/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve"
# Campanha engine-updates-2026-10: runtimes atualizados e pesos do 27B.
OPT="$HOME/.local/opt/qwen38"
MC27="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
DFLASH2="$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4"
M27PACK="$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-1d5087d2062c02b279180a53e4016cf9cd7a3d7e"
OQ8E="$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-mtp-c99e5aad8a478f71c10b9a3dde6709158b690da6"
# YaRN do 27B (qwen3_5, mrope): o override repete os campos mrope do config original.
YARN27_JSON() { echo "{\"text_config\":{\"rope_parameters\":{\"mrope_interleaved\":true,\"mrope_section\":[11,11,10],\"partial_rotary_factor\":0.25,\"rope_theta\":10000000,\"rope_type\":\"yarn\",\"factor\":$1,\"original_max_position_embeddings\":262144},\"max_position_embeddings\":$2}}"; }

# Por candidato: launcher, arm, porta, binario, python do probe, tokenizer, metrics.
MODEL_ID_PREF=""; PROBE_SESSION_HEADER=""; PROBE_PRIME_MAX_TOKENS=""
case "$CAND" in
  c1) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.9.2
      MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve
      # mlx-serve /metrics exposes no MTP counter (acceptance comes from the
      # server log via attach_mtp), so skip it entirely and avoid the
      # intermittent connection-reset race on that endpoint.
      METRICS=""
      export QWEN38_MLX_SERVE_BIN="$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve" MLX_SERVE_EXPECTED_VERSION=26.9.2
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="v26.9.2-yarn${YARN}-kv8"
      fi ;;
  u1) # uncensored (abliterated), mesmo pack mlx-serve mixed-4/8 do c1: so os pesos mudam.
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.9.2
      MODEL_DIR="$U1DIR"; MODEL_REV=9ebf9993b1eaec96aec938bf883601b51a90393b
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve
      METRICS=""
      export QWEN38_MLX_SERVE_BIN="$HOME/.local/opt/qwen38/mlx-serve-v26.9.2/mlx-serve"
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="v26.9.2-yarn${YARN}-kv8"
      fi ;;
  u2) # heretic-2 oQ4e, mesmo runtime oMLX dev2 do c3.
      LAUNCHER="$HARNESS/run-omlx.sh"; ARM=FN; PORT=8000; RUNTIME=omlx; REV=v0.7.0.dev2
      MODEL_DIR="$U2DIR"; MODEL_REV=65b0cd6
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      PROBE_PY="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/python"
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_OMLX_BIN="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2 ;;
  n1|n2|n2p) # flashnext-updates-2026-10: runtime 26.10.1. n1 = pesos do c1; n2/n2p = pack iQ; n2p = + --ple-gpu.
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.1
      if [[ "$CAND" == n1 ]]; then
        MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      else
        MODEL_DIR="$IQDIR"; MODEL_REV=dafff5c3d8168c9d13275661153911096499a80a
      fi
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve
      METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26101" MLX_SERVE_EXPECTED_VERSION=26.10.1
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      if [[ "$CAND" == n2p ]]; then
        export QWEN38_MLX_PLE_GPU=1; REV=v26.10.1-plegpu
      fi
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="v26.10.1-yarn${YARN}-kv8"
      fi ;;
  r27|r27b) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=C; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.1
      MODEL_DIR="$MC27"; MODEL_REV=815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26101" MLX_SERVE_EXPECTED_VERSION=26.10.1
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX" QWEN38_MLX_DRAFTER="$DFLASH2"
      export QWEN38_MLX_PREFIX_CACHE_MEM=16GB QWEN38_MLX_PREFIX_CACHE_DISK=100GB QWEN38_MLX_PREFIX_CACHE_ENTRIES=64
      if [[ "$CAND" == r27b ]]; then export QWEN38_MLX_DRAFT_BLOCK_SIZE=5; REV=v26.10.1-blk5; else unset QWEN38_MLX_DRAFT_BLOCK_SIZE; fi
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8 QWEN38_MLX_CONFIG_OVERRIDES="$(YARN27_JSON "$YARN" "$CTX")"
        REV="v26.10.1-yarn${YARN}-kv8"
      fi ;;
  m1|m1b|m1t|m1h|m1th|m1p|m1hp|m27|m27f)
      LAUNCHER="$HARNESS/run-mtplx.sh"; PORT=8000; RUNTIME=MTPLX; REV=v2.12.2
      PROBE_PY="$OPT/mtplx-v2.12.2/bin/python"; METRICS="http://127.0.0.1:$PORT/metrics"; SERVER_NAME=mtplx
      export QWEN38_MTPLX_BIN="$OPT/mtplx-v2.12.2/bin/mtplx" QWEN38_MTPLX_EXPECTED_VERSION=2.12.2 QWEN38_CTX_SIZE="$CTX"
      if [[ "$CAND" == m27 || "$CAND" == m27f ]]; then
        ARM=V2; MODEL_DIR="$M27PACK"; MODEL_REV=1d5087d2062c02b279180a53e4016cf9cd7a3d7e
      else
        ARM=FX; MODEL_DIR="$MTPLXPACK"; MODEL_REV=6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6
      fi
      # Só o m1b muda o limite; um valor herdado do shell rodaria m1/m27 fora do default com rótulo v2.12.2.
      if [[ "$CAND" == m1b ]]; then export MTPLX_MEMORY_LIMIT_BYTES=96G; REV=v2.12.2-mem96g; else unset MTPLX_MEMORY_LIMIT_BYTES; fi
      # Etapa F: o knob vem do nome do braço (m27f lê ENGINE_M27F); os outros braços nunca herdam o pin TTL.
      case "$CAND" in
        m1t) FIX=pin0 ;; m1h) FIX=sesshdr ;; m1th) FIX=pin0-sesshdr ;;
        m1p) FIX=prime64 ;; m1hp) FIX=sesshdr-prime64 ;;
        m27f) FIX="${ENGINE_M27F:?m27f exige ENGINE_M27F=pin0|sesshdr|prime64|sesshdr-prime64|...}" ;;
        *) FIX="" ;;
      esac
      unset MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S
      [[ "$FIX" == *pin0* ]] && export MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S=0
      [[ "$FIX" == *sesshdr* ]] && PROBE_SESSION_HEADER=x-mtplx-session-id
      # O MTPLX trata um pedido sem histórico e com max_tokens <= 48 como tarefa de background (sem sessão):
      # todo braço MTPLX usa prime de 64 tokens, salvo os diagnósticos da Etapa F que medem o prime de 1 token.
      case "$FIX" in pin0|sesshdr|pin0-sesshdr) ;; *) PROBE_PRIME_MAX_TOKENS=64 ;; esac
      [[ -n "$FIX" ]] && REV="v2.12.2-$FIX"
      TOKENIZER="$MODEL_DIR"
      if [[ -n "$YARN" ]]; then
        YARN_MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-flashnext-overlays/yarn${YARN%%.*}"
        YARN_MODEL_DIR="$YARN_MODEL_ROOT/$(basename "$MODEL_DIR")"
        [[ -d "$YARN_MODEL_DIR" ]] || { echo "run-candidate: rode scripts/make-yarn-overlay.py --src $MODEL_DIR --dst-root $YARN_MODEL_ROOT --factor $YARN --ctx $CTX" >&2; exit 66; }
        MODEL_DIR="$YARN_MODEL_DIR"; TOKENIZER="$YARN_MODEL_DIR"; REV="${REV}-yarn${YARN}"
      fi ;;
  o1|o27)
      LAUNCHER="$HARNESS/run-omlx.sh"; PORT=8000; RUNTIME=omlx; REV=v0.7.0
      if [[ "$CAND" == o1 ]]; then ARM=FN; MODEL_DIR="$OQ4E"; MODEL_REV=2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8
      else ARM=T; MODEL_DIR="$OQ8E"; MODEL_REV=c99e5aad8a478f71c10b9a3dde6709158b690da6; fi
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      PROBE_PY="$OPT/omlx-v0.7.0/bin/python"
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_OMLX_BIN="$OPT/omlx-v0.7.0/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.0 ;;
  s27|s27g|s27r) LAUNCHER="$HARNESS/run-mlx-dspark.sh"; ARM=S; PORT=8484; RUNTIME=mlx-dspark; REV=v0.20.3
      MODEL_DIR="$MC27"; MODEL_REV=815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=mlx-dspark
      PROBE_PY="$OPT/mlx-dspark-v0.20.3/bin/python"
      export MLX_DSPARK_BIN="$OPT/mlx-dspark-v0.20.3/bin/mlx-dspark" QWEN38_MLX_DSPARK_EXPECTED_VERSION=0.20.3
      export MLX_DSPARK_TARGET_PATH="$MC27" MLX_DSPARK_DFLASH2_PATH="$DFLASH2" QWEN38_CTX_SIZE="$CTX"
      unset QWEN38_MLX_DSPARK_NO_MEMORY_GUARD QWEN38_MLX_DSPARK_RUNGS
      [[ "$CAND" == s27g ]] && { export QWEN38_MLX_DSPARK_NO_MEMORY_GUARD=1; REV=v0.20.3-noguard; }
      [[ "$CAND" == s27r ]] && { export QWEN38_MLX_DSPARK_RUNGS=1024; REV=v0.20.3-rungs1024; }
      : ;;
  d1) LAUNCHER="$HARNESS/run-ds4.sh"; ARM=FD; PORT=11234; RUNTIME=ds4
      MODEL_DIR="$OPT/ds4-upstream"; MODEL_REV=qwen38-q4k
      REV="upstream-$(git -C "$MODEL_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
      TOKENIZER="$IQDIR"; METRICS=""; SERVER_NAME=ds4-server
      # ds4-server serve qwen3.8-flash-next, -chat e -reasoner: o probe usa o id base.
      MODEL_ID_PREF=qwen3.8-flash-next
      PROBE_PY="$OPT/mtplx-v2.12.2/bin/python"
      export QWEN38_CTX_SIZE="$CTX" ;;
  c2|c3)
      LAUNCHER="$HARNESS/run-omlx.sh"; ARM=FN; PORT=8000; RUNTIME=omlx
      MODEL_DIR="$OQ4E"; MODEL_REV=2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      if [[ "$CAND" == c2 ]]; then
        REV=v0.6.4; PROBE_PY="$HOME/.local/share/uv/tools/omlx/bin/python"
        export QWEN38_OMLX_BIN="$HOME/.local/share/uv/tools/omlx/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.6.4
      else
        REV=v0.7.0.dev2; PROBE_PY="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/python"
        export QWEN38_OMLX_BIN="$HOME/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2
      fi ;;
  c4) LAUNCHER="$HARNESS/run-mtplx.sh"; ARM=FX; PORT=8000; RUNTIME=MTPLX; REV=v2.11.2
      MODEL_DIR="$MTPLXPACK"; MODEL_REV=6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6
      PROBE_PY="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/python"; TOKENIZER="$MODEL_DIR"
      METRICS="http://127.0.0.1:$PORT/metrics"; SERVER_NAME=mtplx
      export QWEN38_MTPLX_BIN="$HOME/.local/opt/qwen38/mtplx-v2.11.2/bin/mtplx" QWEN38_MTPLX_EXPECTED_VERSION=2.11.2
      export QWEN38_CTX_SIZE="$CTX"
      PROBE_PRIME_MAX_TOKENS=64  # prime de 1 token roda sem sessão no MTPLX (ver m1 acima)
      [[ -n "$GENMODE" ]] && export QWEN38_MTPLX_GENERATION_MODE="$GENMODE"
      [[ -n "$GENMODE" && "$GENMODE" != mtp ]] && REV="v2.11.2-${GENMODE}"
      # --yarn F: MTPLX 2.11.2's qwen4_exp code implements static YaRN correctly
      # but has no runtime flag to inject rope_type/factor/original_max_position_embeddings
      # (task-11-yarn-mapping.md) -- the only way in is a config.json baked ahead of
      # time by scripts/make-yarn-overlay.py. Point the launcher at that overlay root
      # instead of the plain prefix-cache root, and serve/probe from the overlay dir.
      if [[ -n "$YARN" ]]; then
        YARN_MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-flashnext-overlays/yarn${YARN%%.*}"
        YARN_MODEL_DIR="$YARN_MODEL_ROOT/$(basename "$MTPLXPACK")"
        [[ -d "$YARN_MODEL_DIR" ]] || {
          echo "run-candidate: overlay model dir missing: $YARN_MODEL_DIR" >&2
          echo "run-candidate: run scripts/make-yarn-overlay.py --src $MTPLXPACK --dst-root $YARN_MODEL_ROOT --factor $YARN --ctx $CTX first" >&2
          exit 66
        }
        # The overlay dir is named yarn${factor%%.*}, so e.g. factor 2.0 and
        # 2.5 alias to the same "yarn2" dir -- existence alone doesn't prove
        # this overlay was actually built for THIS factor/ctx. Read its
        # patched config.json back and compare, so a stale/mismatched overlay
        # fails loudly instead of silently serving the wrong rope scaling.
        YARN_CHECK="$(python3 -c '
import json, sys
path, want_factor, want_ctx = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
cfg = json.load(open(path))
tc = cfg.get("text_config", cfg)
rope = tc.get("rope_parameters") or tc.get("rope_scaling") or {}
found_factor = rope.get("factor")
found_ctx = tc.get("max_position_embeddings")
ok = (
    found_factor is not None
    and found_ctx is not None
    and abs(float(found_factor) - want_factor) < 1e-9
    and int(found_ctx) == want_ctx
)
print(f"{int(ok)} {found_factor} {found_ctx}")
' "$YARN_MODEL_DIR/config.json" "$YARN" "$CTX")"
        read -r YARN_OK YARN_FOUND_FACTOR YARN_FOUND_CTX <<<"$YARN_CHECK"
        [[ "$YARN_OK" == "1" ]] || {
          echo "run-candidate: overlay config mismatch at $YARN_MODEL_DIR/config.json: found factor=$YARN_FOUND_FACTOR ctx=$YARN_FOUND_CTX, wanted factor=$YARN ctx=$CTX" >&2
          echo "run-candidate: rebuild with: python3 $HERE/scripts/make-yarn-overlay.py --src $MTPLXPACK --dst-root $YARN_MODEL_ROOT --factor $YARN --ctx $CTX" >&2
          exit 66
        }
        MODEL_DIR="$YARN_MODEL_DIR"; TOKENIZER="$YARN_MODEL_DIR"
        REV="v2.11.2-yarn${YARN}"
      fi ;;
  *) echo "candidato desconhecido: $CAND" >&2; exit 64 ;;
esac
export QWEN38_MODEL_ROOT="$MODEL_ROOT"
# c4 --yarn points the launcher at the overlay root instead; must win over the
# line above (which is unconditional for every other candidate/path).
[[ -n "${YARN_MODEL_ROOT:-}" ]] && export QWEN38_MODEL_ROOT="$YARN_MODEL_ROOT"
BASE="http://127.0.0.1:$PORT"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
# --tag given: name stays exactly "<cand>-<ctx>-t<temp>-<tag>" (a pending run
# depends on this, e.g. c1-524288-t1.0-yarn2 from --yarn 2.0 --tag yarn2).
# --tag omitted: fold --yarn/--generation-mode into the name so an untagged
# YaRN or non-mtp run never collides with (or overwrites) the base variant's
# file -- mtp is the default generation mode so it never suffixes the name.
if [[ -n "$TAG" ]]; then
  NAME="${CAND}-${CTX}-t${TEMP}-${TAG}"
else
  NAME="${CAND}-${CTX}-t${TEMP}"
  [[ -n "$YARN" ]] && NAME="${NAME}-yarn${YARN}"
  [[ -n "$GENMODE" && "$GENMODE" != "mtp" ]] && NAME="${NAME}-${GENMODE}"
fi
OUT="$RESULTS/$NAME.jsonl"; BOOT="$LOGS/$NAME-boot.log"; MEM="$LOGS/$NAME-mem.jsonl"

# Etapa B: with REPEAT>1 pin middle_mutation (prefill-bound, deterministic) to
# a single rep and spend the extra reps on the cache-reuse scenarios instead;
# cache_probe.py already supports --scenario-repeats for this. REPEAT=1 keeps
# the probe invocation unchanged.
SCENARIO_REPEATS=""
[[ "$REPEAT" -gt 1 ]] && SCENARIO_REPEATS="middle_mutation=1"

# Id servido que o probe usa: o nome do diretório do modelo, salvo quando o candidato declara outro.
MODEL_SELECT="${MODEL_ID_PREF:-$(basename "$MODEL_DIR")}"
if [[ -n "$PRINT" ]]; then
  echo "model_select: $MODEL_SELECT"
  echo "launcher: $LAUNCHER $ARM"; bash "$LAUNCHER" "$ARM" --print; echo
  echo "probe: $PROBE_PY cache_probe.py --base-url $BASE/v1 --runtime $RUNTIME --runtime-revision $REV --context $CTX --repeat $REPEAT --temperature $TEMP ${SCENARIOS:+--scenarios $SCENARIOS} ${TOKENIZER:+--tokenizer-path $TOKENIZER} ${METRICS:+--metrics-url $METRICS} ${SCENARIO_REPEATS:+--scenario-repeats $SCENARIO_REPEATS} ${PROBE_SESSION_HEADER:+--session-header $PROBE_SESSION_HEADER} ${PROBE_PRIME_MAX_TOKENS:+--prime-max-tokens $PROBE_PRIME_MAX_TOKENS}"
  echo "saida: $OUT"; exit 0
fi

# O binário errado invalida o A/B inteiro: conferir a versão antes de subir o servidor.
if [[ -n "${MLX_SERVE_EXPECTED_VERSION:-}" ]]; then
  GOT_VERSION="$("$QWEN38_MLX_SERVE_BIN" --version 2>&1 | grep '^mlx-serve ' || true)"
  if [[ "$GOT_VERSION" != "mlx-serve $MLX_SERVE_EXPECTED_VERSION" ]]; then
    echo "run-candidate: $QWEN38_MLX_SERVE_BIN reporta '$GOT_VERSION', esperado 'mlx-serve $MLX_SERVE_EXPECTED_VERSION'" >&2
    exit 65
  fi
fi

mkdir -p "$RESULTS" "$LOGS"

# cache_probe.py appends to --output, and mem-sampler.sh appends to its own
# output too -- neither ever truncates on its own (other campaigns rely on
# that append behavior in cache_probe.py). Without rotating here, a second
# run under the same name (a retry, or an untagged run sharing a name with an
# earlier one) would append its records onto a stale prior run's JSONL/
# memory-sample file instead of starting clean, silently inflating `n` and
# corrupting the medians summarize_driver computes downstream.
if [[ -s "$OUT" ]]; then
  BAK="$OUT.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  mv "$OUT" "$BAK"
  echo "    $NAME: OUT pre-existente movido para $BAK"
fi
: > "$MEM"

SERVER_PID=""; SAMPLER_PID=""
cleanup() {
  [[ -n "$SAMPLER_PID" ]] && kill "$SAMPLER_PID" 2>/dev/null || true
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
  # SERVER_PID is the `nohup bash "$LAUNCHER" ...` wrapper, not necessarily the
  # runtime process itself -- kill whatever is actually listening on $PORT too,
  # or a dead probe leaves the server (and the port) held by an orphan.
  local listeners
  listeners="$(lsof -nP -tiTCP:${PORT} -sTCP:LISTEN 2>/dev/null || true)"
  [[ -n "$listeners" ]] && kill $listeners 2>/dev/null || true
}
trap cleanup EXIT

wait_port_free() { for _ in $(seq 1 30); do lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1 || return 0; sleep 1; done; echo "porta $PORT nao liberou" >&2; return 1; }
wait_mem_free() {
  local need="${1:-82}" free
  for _ in $(seq 1 24); do
    free="$(python3 -c 'import re,subprocess;o=subprocess.check_output(["vm_stat"]).decode();ps=int(re.search(r"page size of (\d+)",o).group(1));m=re.search(r"Pages free:\s+(\d+)\.",o);print(int(m.group(1))*ps/1e9)')"
    awk "BEGIN{exit !($free >= $need)}" && { echo "    memoria livre ~${free} GB (>= $need)"; return 0; }
    sleep 5
  done
  echo "    aviso: memoria nao assentou em 120s; seguindo" >&2
}
server_ready() { curl -fsS --max-time 3 "$BASE/v1/models" >/dev/null 2>&1; }

wait_port_free; wait_mem_free 82
# cold tem que ser frio: o disco de prefix-cache do mlx-serve persiste entre restarts (rodada 1 do P1
# foi descartada por isso). oMLX e MTPLX gravam sob logs/<run-id>, novo a cada subida.
if [[ -d "$HOME/.mlx-serve/kv-cache" ]]; then echo "    limpando ~/.mlx-serve/kv-cache"; rm -rf "$HOME/.mlx-serve/kv-cache/"* 2>/dev/null || true; fi

echo ">>> $NAME: sampler + servidor ($LAUNCHER $ARM)"
bash "$HERE/scripts/mem-sampler.sh" "$MEM" "$SERVER_NAME" 5 & SAMPLER_PID=$!
nohup bash "$LAUNCHER" "$ARM" >"$BOOT" 2>&1 & SERVER_PID=$!
ready=""
for _ in $(seq 1 200); do
  server_ready && { ready=1; break; }
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "servidor morreu no boot; ver $BOOT" >&2; exit 69; }
  sleep 3
done
[[ -n "$ready" ]] || { echo "servidor nao ficou pronto em 10 min; ver $BOOT" >&2; exit 69; }
MODELS_JSON="$(curl -fsS "$BASE/v1/models")"
MODEL_BASENAME="$MODEL_SELECT"
MODEL_ID="$(python3 -c '
import sys, json
data = json.load(sys.stdin)["data"]
ids = [m["id"] for m in data]
basename = sys.argv[1]
if basename in ids:
    print(basename)
elif len(ids) == 1:
    print(ids[0])
else:
    print(f"nenhum id casa com basename={basename!r} entre {len(ids)} ids servidos: {ids}", file=sys.stderr)
    sys.exit(1)
' "$MODEL_BASENAME" <<<"$MODELS_JSON")" || true
[[ -n "$MODEL_ID" ]] || { echo "run-candidate: could not select model id for $CAND (basename=$MODEL_BASENAME); see /v1/models" >&2; exit 69; }
echo ">>> $NAME: model_id=$MODEL_ID"
echo ">>> $NAME: pronto. model_id=$MODEL_ID -> $OUT"
# /props (mlx-serve >= 26.9.4) mostra MTP, KV quant e PLD em vigor. O 26.9.2 não tem o endpoint.
if [[ "$RUNTIME" == mlx-serve ]]; then
  mkdir -p "$RESULTS/props"
  if curl -fsS --max-time 10 "$BASE/props" >"$RESULTS/props/$NAME.json" 2>/dev/null \
     || curl -fsS --max-time 10 "$BASE/v1/props" >"$RESULTS/props/$NAME.json" 2>/dev/null; then
    echo "    /props -> $RESULTS/props/$NAME.json"
  else
    rm -f "$RESULTS/props/$NAME.json"; echo "    /props indisponivel neste binario"
  fi
fi

# Probe can exit non-zero on purpose (e.g. a memory-guard HTTP refusal was
# recorded as data) -- capture that instead of letting `set -e` abort before
# cleanup runs (attach_memory/attach_mtp on whatever records exist, kill the
# server). `|| PROBE_EXIT=$?` keeps errexit happy since the assignment itself
# succeeds.
PROBE_EXIT=0
"$PROBE_PY" "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" --model "$MODEL_ID" --api-model "$MODEL_ID" \
  --runtime "$RUNTIME" --runtime-revision "$REV" --model-revision "$MODEL_REV" \
  --arm "$CAND" --session-id "${TS}-${NAME}" \
  --context "$CTX" --content-class audit_retrieval --repeat "$REPEAT" \
  --temperature "$TEMP" --top-p 0.95 --top-k 20 --reasoning-effort xhigh \
  ${SCENARIOS:+--scenarios "$SCENARIOS"} \
  ${TOKENIZER:+--tokenizer-path "$TOKENIZER"} \
  ${METRICS:+--metrics-url "$METRICS"} \
  ${SCENARIO_REPEATS:+--scenario-repeats "$SCENARIO_REPEATS"} \
  ${PROBE_SESSION_HEADER:+--session-header "$PROBE_SESSION_HEADER"} \
  ${PROBE_PRIME_MAX_TOKENS:+--prime-max-tokens "$PROBE_PRIME_MAX_TOKENS"} \
  --output "$OUT" --cache-enabled $([[ "$GENMODE" == "" || "$GENMODE" == mtp ]] && echo --mtp-enabled) \
  || PROBE_EXIT=$?

kill "$SAMPLER_PID" 2>/dev/null || true; SAMPLER_PID=""
python3 "$HERE/scripts/attach_memory.py" --results "$OUT" --sampler "$MEM" || true
python3 "$HERE/scripts/attach_mtp.py" --results "$OUT" --log "$BOOT" || true
kill "$SERVER_PID" 2>/dev/null || true; SERVER_PID=""
# Every command from here on must be guarded: under `set -e` a non-zero
# return (e.g. wait_port_free timing out) would abort before `exit
# "$PROBE_EXIT"`, silently turning a flagged probe failure into a script
# exit of 0 for the supervisor. The EXIT trap still runs cleanup regardless.
wait_port_free || true
if [[ "$PROBE_EXIT" -ne 0 ]]; then
  echo ">>> $NAME: probe exited $PROBE_EXIT (see $OUT for any refusal records)" >&2
else
  echo ">>> $NAME: OK"
fi
exit "$PROBE_EXIT"
