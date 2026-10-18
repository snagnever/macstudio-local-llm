#!/usr/bin/env bash
# Driver unico da campanha flashnext-daily-driver: sobe UM candidato, roda o cache_probe com o
# perfil do vendor, amostra memoria e derruba o servidor. Um candidato por vez.
#   c1 = ddalcu mixed-4/8 @ mlx-serve 26.9.2      c2 = Jundot oQ4e @ oMLX 0.6.4
#   c3 = Jundot oQ4e @ oMLX 0.7.0.dev2            c4 = MTPLX Optimized-Speed @ MTPLX 2.11.2
#   n1/n2/n2p = campanha flashnext-updates-2026-10 (mlx-serve 26.10.1; n2 = pack iQ-MLX-4.7bpw; n2p = n2 + --ple-gpu)
#   w1 = campanha swift15-flashnext-2026-10: Swift 1.5 (Dankpaws MLX-4.7bpw) @ mlx-serve 26.10.1, flags do n2
#   engine-updates-2026-10: m1/m1b = MTPLX 2.12.2 (m1b: limite 96G), o1 = oMLX 0.7.0, d1 = ds4 upstream;
#   r27 = 27B @ mlx-serve 26.10.1 + DFlash2, m27 = MTPLX 2.12.2, o27 = oMLX 0.7.0, s27 = mlx-dspark 0.20.3
#   Etapa F (um knob por braço): m1t/m1h/m1th = m1 + pin TTL 0 / header de sessão / os dois;
#   m1p/m1hp = m1 + prime com 64 tokens / + header de sessão;
#   m27f = m27 + knob de ENGINE_M27F; r27b = r27 + --draft-block-size 5; s27g = s27 + --no-memory-guard;
#   s27r = s27 + --prefix-cache-rungs 1024
#   qwen38-27b-next-steps-2026-10: o27q8/o27q4/o27sw = oMLX 0.7.1.dev1 + Jundot oQ8e/oQ4e refit and Swift 1.5 oQ4e;
#   r27d = ddalcu 27B 8bit @ mlx-serve 26.10.2 (bundled DFlash2 drafter only, --no-mtp), r27m = same pack with
#   --no-drafter (MTP only); mlx-serve speculation priority is MTP > drafter > PLD, so each arm switches the other off;
#   w27d/w27m = the same two modes on the Swift 1.5 oQ4e pack (w27d borrows the ddalcu drafter);
#   k27 = Splash 1.3.1 + mlx-community 8bit; l27/l27n = llama.cpp b11569 Q8_0 with/without MTP draft
#   flashnext-concurrency-2026-10: w1c1..w1c2m4q8 = w1 with --max-concurrent N and N parallel probe streams
set -euo pipefail

CAND="${1:?uso: $0 <c1|c2|c3|c4|u1|u2|n1|n2|n2p|n2o|n2o2|n2q4|w1|m1|m1b|m1t|m1h|m1th|m1p|m1hp|m1v|m1x|m1q|m1xq|m1s|o1|d1|r27|r27b|m27|m27f|o27|s27|s27g|s27r|n2x|n2xd|w1x|w1q4|w1xq4|w1c8|w1xc8|w1p8|w1xp8|o1rm|s1m|w1t|n2t|o1x|o1r|x1|g0|g1|g1m|o27q8|o27q4|o27sw|r27d|r27m|w27d|w27m|k27|l27|l27n|w1c1|w1c1a|w1c1x2|w1c2|w1c2a|w1c2m8|w1c4|w1c4a|w1c2L|w1c2m4|w1c2q8|w1c2m4q8|w1c2ap3|w1c2ap5|w1c3a> <ctx> [--scenarios a,b] [--repeat N] [--temperature T] [--tag X] [--yarn F] [--generation-mode M] [--exec CMD] [--print]}"
CTX="${2:?ctx obrigatorio}"; shift 2
SCENARIOS=""; REPEAT=1; TEMP=1.0; TAG=""; YARN=""; GENMODE=""; PRINT=""; EXEC_CMD=""
# A bateria troca o probe só quando o chamador passa --exec. Um FLASHNEXT_EXEC herdado do shell é ignorado.
if [[ -n "${FLASHNEXT_EXEC:-}" ]]; then
  echo "run-candidate: FLASHNEXT_EXEC no ambiente é ignorado; use --exec" >&2
  unset FLASHNEXT_EXEC
fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenarios) SCENARIOS="$2"; shift 2 ;;
    --repeat) REPEAT="$2"; shift 2 ;;
    --temperature) TEMP="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --yarn) YARN="$2"; shift 2 ;;
    --generation-mode) GENMODE="$2"; shift 2 ;;
    --exec) EXEC_CMD="$2"; shift 2 ;;
    --print) PRINT=1; shift ;;
    *) echo "opcao desconhecida: $1" >&2; exit 64 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HARNESS="$REPO/bench/qwen3.8-prefix-cache/scripts"
HERE="$REPO/bench/qwen38-flashnext-daily-driver-2026-09"
# Outra campanha pode reusar este driver apontando a saída para o próprio diretório.
RESULTS="${FLASHNEXT_RESULTS_DIR:-$HERE/results}"; LOGS="${FLASHNEXT_LOGS_DIR:-$HERE/logs}"
EFFORT="${FLASHNEXT_EFFORT:-xhigh}"
case "$EFFORT" in xhigh|medium|low) ;; *) echo "run-candidate: FLASHNEXT_EFFORT must be xhigh, medium or low: $EFFORT" >&2; exit 64 ;; esac
MODEL_ROOT="$HOME/.cache/local-llms/qwen3.8-prefix-cache"
DDALCU="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit-ef5b919d31534faa1997666f1a22d362cd6383cd"
OQ4E="$MODEL_ROOT/Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8"
MTPLXPACK="$MODEL_ROOT/Youssofal-Qwen3.8-Flash-Next-MTPLX-Optimized-Speed-6bc2f6e8426ccb4af73c81bc56ba7718afc92cc6"
# Etapa U: variantes uncensored, mesmo runtime/layout dos candidatos de referencia.
U1DIR="$MODEL_ROOT/ARC4NUM-Qwen3.8-Flash-Next-Uncensored-MLX-Serve-4bit-9ebf9993b1eaec96aec938bf883601b51a90393b"
U2DIR="$MODEL_ROOT/latent-variable-Qwen3.8-Flash-Next-heretic-2-oQ4e-mtp-65b0cd6"
# Campanha flashnext-updates-2026-10: pack calibrado (mesmo layout do DDALCU) e runtime 26.10.1.
IQDIR="$MODEL_ROOT/ddalcu-Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-4.7bpw-dafff5c3d8168c9d13275661153911096499a80a"
# Campanha swift15-flashnext-2026-10: fine-tune Swift 1.5, mesmo layout e runtime do IQDIR.
SWIFTDIR="$MODEL_ROOT/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0"
MLXSERVE_26101="$HOME/.local/opt/qwen38/mlx-serve-v26.10.1/mlx-serve"
# Campanha engine-updates-2026-10: runtimes atualizados e pesos do 27B.
OPT="$HOME/.local/opt/qwen38"
# Campaign flashnext-next-steps-2026-10: runtimes installed by its scripts/install-runtime.sh and packs downloaded
# by its scripts/fetch_pack.py (directory names end in the full revision; pack_dir resolves the prefix).
# Stable 26.10.2 (2026-10-12) replaced pre-release.1: it adds the f32 GDN state (#815) and the n-gram
# prefill calibration fix (#821).
MLXSERVE_26102="$OPT/mlx-serve-v26.10.2/mlx-serve"
MLXSERVE_26102_VERSION=26.10.2
OMLX_0711="$OPT/omlx-v0.7.1.dev1"
# Flash-Next oMLX arms (o1x, o1r, x1): dev2 (2026-10-15) keeps GDN state exact on padded prefill (#4526) and cuts
# fp16 Flash-Next prefill memory (89a40d113). The 27B arms keep dev1.
OMLX_0712="$OPT/omlx-v0.7.1.dev2"
LLAMA_B11569="$OPT/llama-b11569/llama-server"
# Flash-Next GGUF arms: b11600+ stops pinning the lazy per-layer-embedding tensor in the GPU buffer (#30405).
LLAMA_B11609="$OPT/llama-b11609/llama-server"
pack_dir() {
  local m=("$MODEL_ROOT/$1"*)
  if [[ -e "${m[0]}" ]]; then echo "${m[0]}"; else echo "$MODEL_ROOT/$1-MISSING"; fi
}
MC27="$MODEL_ROOT/mlx-community--Qwen3.8-27B-8bit-815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9"
DFLASH2="$MODEL_ROOT/incoai--Qwen3.8-27B-DFlash2-dedf8df68adfb1afeaf7b7480c0a0243108177b4"
M27PACK="$MODEL_ROOT/Youssofal-Qwen3.8-27B-MTPLX-Optimized-Speed-1d5087d2062c02b279180a53e4016cf9cd7a3d7e"
OQ8E="$MODEL_ROOT/Jundot-Qwen3.8-27B-oQ8e-mtp-c99e5aad8a478f71c10b9a3dde6709158b690da6"
# Campaign qwen38-27b-next-steps-2026-10: final mlx-serve 26.10.2, Splash 1.3.1 and the dense 27B packs
# (pack_dir returns a -MISSING path when a pack is not on disk: --print still works, a real run exits 66).
MLXSERVE_26102F="$OPT/mlx-serve-v26.10.2/mlx-serve"
DD27="$(pack_dir ddalcu-Qwen3.8-27B-MLX-Serve-8bit-7775059e955f)"
OQ8E_R="$(pack_dir Jundot-Qwen3.8-27B-oQ8e-mtp-6c76ddfb82af)"
OQ4E_R="$(pack_dir Jundot-Qwen3.8-27B-oQ4e-mtp-49c1d60367d9)"
SW27="$(pack_dir scottlowry-Swift-1.5-Qwen3.8-27b-oQ4e-mtp-881dc1914f65)"
GGUF27="$(pack_dir ggml-org-Qwen3.8-27B-GGUF-71bc7b627595)"
# YaRN do 27B (qwen3_5, mrope): o override repete os campos mrope do config original.
YARN27_JSON() { echo "{\"text_config\":{\"rope_parameters\":{\"mrope_interleaved\":true,\"mrope_section\":[11,11,10],\"partial_rotary_factor\":0.25,\"rope_theta\":10000000,\"rope_type\":\"yarn\",\"factor\":$1,\"original_max_position_embeddings\":262144},\"max_position_embeddings\":$2}}"; }

# Por candidato: launcher, arm, porta, binario, python do probe, tokenizer, metrics.
MODEL_ID_PREF=""; PROBE_SESSION_HEADER=""; PROBE_PRIME_MAX_TOKENS=""
# QWEN38_PROBE_MAX_TOKENS (optional): --max-tokens of cache_probe.py; the fixture shrinks by the same amount.
# --os-reserve-gib só no braço n2o: um valor herdado do shell não vale para os outros braços.
unset QWEN38_MLX_OS_RESERVE_GIB
# Extra mlx-serve flags only for the n2xd arm (flashnext-next-steps-2026-10); a shell value never leaks.
unset QWEN38_MLX_EXTRA_ARGS
ARM_EXEC=""
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
  n1|n2|n2p|n2o|n2o2|n2q4|w1) # flashnext-updates-2026-10: runtime 26.10.1. n1 = pesos do c1; n2/n2p/n2o = pack iQ; n2p = + --ple-gpu; w1 = Swift 1.5.
      # n2o = n2 + --os-reserve-gib 4 (default 8 GB no Mac de 128 GB): o PrefillDoesNotFit a 512K faltou 0.6–3.2 GB.
      # n2o2 = reserva 2 GB: com 4 GB um prime ainda recusou por ~0.3 GB; com 3 reps virou OOM de Metal.
      # n2q4 = KV 4-bit a 512K com a reserva padrão: reduz a cópia de KV (~9 GB com KV 8-bit).
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.1
      if [[ "$CAND" == n1 ]]; then
        MODEL_DIR="$DDALCU"; MODEL_REV=ef5b919d31534faa1997666f1a22d362cd6383cd
      elif [[ "$CAND" == w1 ]]; then
        MODEL_DIR="$SWIFTDIR"; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0
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
      fi
      if [[ "$CAND" == n2o ]]; then export QWEN38_MLX_OS_RESERVE_GIB=4; REV="${REV}-osr4"; fi
      if [[ "$CAND" == n2o2 ]]; then export QWEN38_MLX_OS_RESERVE_GIB=2; REV="${REV}-osr2"; fi
      if [[ "$CAND" == n2q4 && -n "$YARN" ]]; then export QWEN38_MLX_KV_QUANT=4; REV="v26.10.1-yarn${YARN}-kv4"; fi ;;
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
  m1|m1b|m1t|m1h|m1th|m1p|m1hp|m1v|m1x|m1q|m1xq|m1s|m27|m27f)
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
        m1v) FIX=vendor ;; m1x) FIX=memmax ;; m1q) FIX=kvq8 ;;
        m1xq) FIX=memmax-kvq8 ;;  # os dois juntos: a conta do memory plan só chega a 262K assim
        m1s) FIX=qsaprefill ;;  # prefill esparso do indexer QSA, que o auto só liga com NAX (M5)
        m27f) FIX="${ENGINE_M27F:?m27f exige ENGINE_M27F=pin0|sesshdr|prime64|sesshdr-prime64|...}" ;;
        *) FIX="" ;;
      esac
      unset MTPLX_SESSION_BANK_ACTIVE_PIN_TTL_S QWEN38_MTPLX_VENDOR_DEFAULT QWEN38_MTPLX_MEMORY_LIMIT QWEN38_MTPLX_KV_QUANT MTPLX_QSA_PREFILL
      [[ "$FIX" == qsaprefill ]] && export MTPLX_QSA_PREFILL=1
      # Etapa G: config padrão do vendor, memory limit max e KV q8, um knob por braço.
      [[ "$FIX" == vendor ]] && export QWEN38_MTPLX_VENDOR_DEFAULT=1
      [[ "$FIX" == memmax* ]] && export QWEN38_MTPLX_MEMORY_LIMIT=max
      [[ "$FIX" == *kvq8 ]] && export QWEN38_MTPLX_KV_QUANT=q8
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
  # --- Qwen3.8-27B next steps 2026-10 (bench/qwen38-27b-next-steps-2026-10) ---
  o27q8|o27q4|o27sw) LAUNCHER="$HARNESS/run-omlx.sh"; PORT=8000; RUNTIME=omlx; REV=v0.7.1.dev1
      PROBE_PY="$OMLX_0711/bin/python"; TOKENIZER=""; SERVER_NAME=omlx; METRICS=""
      export QWEN38_OMLX_BIN="$OMLX_0711/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.1.dev1 OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      case "$CAND" in
        o27q8) ARM=T8R; MODEL_DIR="$OQ8E_R"; MODEL_REV=6c76ddfb82af ;;
        o27q4) ARM=T4R; MODEL_DIR="$OQ4E_R"; MODEL_REV=49c1d60367d9 ;;
        o27sw) ARM=TSW; MODEL_DIR="$SW27"; MODEL_REV=881dc1914f65 ;;
      esac
      TOKENIZER="$MODEL_DIR" ;;
  r27d|r27m) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=C; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.2
      MODEL_DIR="$DD27"; MODEL_REV=7775059e955f; PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102F" MLX_SERVE_EXPECTED_VERSION=26.10.2 QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_PREFIX_CACHE_MEM=16GB QWEN38_MLX_PREFIX_CACHE_DISK=100GB QWEN38_MLX_PREFIX_CACHE_ENTRIES=64
      unset QWEN38_MLX_DRAFTER QWEN38_MLX_KV_QUANT QWEN38_MLX_PLE_GPU QWEN38_MLX_DRAFT_BLOCK_SIZE QWEN38_MLX_CONFIG_OVERRIDES
      # Priority is MTP > drafter > PLD: r27m forces MTP alone (--no-drafter), r27d forces the drafter alone (--no-mtp).
      if [[ "$CAND" == r27m ]]; then
        REV=v26.10.2-mtp; export QWEN38_MLX_EXTRA_ARGS="--no-drafter --mtp-max-depth 3"
      else
        REV=v26.10.2-drafter; export QWEN38_MLX_EXTRA_ARGS="--no-mtp"
      fi
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" ;;
  w27d|w27m) LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=C; PORT=11234; RUNTIME=mlx-serve
      MODEL_DIR="$SW27"; MODEL_REV=881dc1914f65; PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102F" MLX_SERVE_EXPECTED_VERSION=26.10.2 QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_PREFIX_CACHE_MEM=16GB QWEN38_MLX_PREFIX_CACHE_DISK=100GB QWEN38_MLX_PREFIX_CACHE_ENTRIES=64
      unset QWEN38_MLX_DRAFTER QWEN38_MLX_KV_QUANT QWEN38_MLX_PLE_GPU QWEN38_MLX_DRAFT_BLOCK_SIZE QWEN38_MLX_CONFIG_OVERRIDES
      # Swift 1.5 27B (oQ4e, MTP head inherited from the base). w27m: MTP alone; w27d: the ddalcu DFlash2 drafter alone.
      if [[ "$CAND" == w27m ]]; then
        REV=v26.10.2-swift-mtp; export QWEN38_MLX_EXTRA_ARGS="--no-drafter --mtp-max-depth 3"
      else
        REV=v26.10.2-swift-drafter; export QWEN38_MLX_EXTRA_ARGS="--no-mtp" QWEN38_MLX_DRAFTER="$DD27/drafter"
      fi
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" ;;
  k27) LAUNCHER="$HARNESS/run-splash.sh"; ARM=K; PORT=8585; RUNTIME=splash; REV=v1.3.1
      MODEL_DIR="$MC27"; MODEL_REV=815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9
      PROBE_PY="$OPT/mlx-dspark-v0.20.3/bin/python"; TOKENIZER="$MC27"; SERVER_NAME=splash; METRICS=""
      # Splash serves the Hub ID as its single model id; MODEL_DIR stays the local pack (probe tokenizer, weights check).
      MODEL_ID_PREF=mlx-community/Qwen3.8-27B-8bit
      export SPLASH_MODEL=mlx-community/Qwen3.8-27B-8bit SPLASH_REVISION=815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9 SPLASH_DRAFTER="$DFLASH2" QWEN38_CTX_SIZE="$CTX" QWEN38_SPLASH_EXPECTED_VERSION=1.3.1 QWEN38_SPLASH_PORT=8585 ;;
  l27|l27n) LAUNCHER="$REPO/bench/qwen38-27b-next-steps-2026-10/scripts/run-llama-27b.sh"; PORT=8080; RUNTIME=llama.cpp; REV=b11569
      MODEL_DIR="$GGUF27"; MODEL_REV=71bc7b627595; PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=llama-server; METRICS=""
      MODEL_ID_PREF=qwen38-27b-gguf
      export QWEN38_GGUF_DIR="$GGUF27" QWEN38_LLAMA_SERVER_BIN="$LLAMA_B11569" QWEN38_CTX_SIZE="$CTX" FLASHNEXT_EFFORT="$EFFORT"
      if [[ "$CAND" == l27 ]]; then ARM=L27M; else ARM=L27N; REV=b11569-nospec; fi ;;
  d1) LAUNCHER="$HARNESS/run-ds4.sh"; ARM=FD; PORT=11234; RUNTIME=ds4
      MODEL_DIR="$OPT/ds4-upstream"; MODEL_REV=qwen38-q4k
      REV="upstream-$(git -C "$MODEL_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
      TOKENIZER="$IQDIR"; METRICS=""; SERVER_NAME=ds4-server
      # ds4-server serve qwen3.8-flash-next, -chat e -reasoner: o probe usa o id base.
      MODEL_ID_PREF=qwen3.8-flash-next
      PROBE_PY="$OPT/mtplx-v2.12.2/bin/python"
      export QWEN38_CTX_SIZE="$CTX"
      # YaRN estático do ds4 (docs/QWEN38_FLASH_NEXT.md): só com --yarn; um valor herdado do shell não vale.
      unset DS4_QWEN4_YARN_FACTOR
      if [[ -n "$YARN" ]]; then export DS4_QWEN4_YARN_FACTOR="$YARN"; REV="${REV}-yarn${YARN}"; fi ;;
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
      unset QWEN38_MTPLX_VENDOR_DEFAULT QWEN38_MTPLX_MEMORY_LIMIT QWEN38_MTPLX_KV_QUANT MTPLX_QSA_PREFILL  # knobs da Etapa G são só do 2.12.2
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
  n2x|n2xd|w1x|w1q4|w1xq4|w1c8|w1xc8|w1p8|w1xp8|o1rm|s1m|w1t|n2t)
      # flashnext-next-steps-2026-10 on mlx-serve. An "x" in the arm = stable 26.10.2 (see line 66), no "x" = 26.10.1.
      # n2x/w1x = n2/w1 flags on 26.10.2; n2xd = n2x + MTP depth (FLASHNEXT_MTP_DEPTH_FLAG, FLASHNEXT_MTP_DEPTH);
      # w1q4/w1xq4 = w1 + 4-bit KV with --yarn (the 512k launcher profile); w1c8/w1xc8 = prefix cache 8GB
      # (control of test #9); w1p8/w1xp8 = w1c8 + --ple-gpu; o1rm = Jundot oQ4e refit c4ddfb5 and
      # s1m = scottlowry Swift 1.5 oQ4e e8ed008, oMLX packs that 26.10.2 loads natively.
      # w1t = w1 from an overlay pack whose chat template puts the effort instruction after the last message
      # (fixes/qwen3.8-flash-next/swift15-effort-tail.jinja, built by scripts/make-overlay.sh of next-steps-2026-10).
      # n2t = n2 from the same kind of overlay (the iQ pack ships the same official template).
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      if [[ "$CAND" == *x* || "$CAND" == o1rm || "$CAND" == s1m ]]; then
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102" MLX_SERVE_EXPECTED_VERSION="$MLXSERVE_26102_VERSION"
        REV="v$MLXSERVE_26102_VERSION"
      else
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26101" MLX_SERVE_EXPECTED_VERSION=26.10.1; REV=v26.10.1
      fi
      case "$CAND" in
        n2x|n2xd) MODEL_DIR="$IQDIR"; MODEL_REV=dafff5c3d8168c9d13275661153911096499a80a ;;
        n2t) MODEL_DIR="$IQDIR-efftail"; MODEL_REV=dafff5c3d8168c9d13275661153911096499a80a; REV="${REV}-efftail" ;;
        w1t) MODEL_DIR="$SWIFTDIR-efftail"; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0; REV="${REV}-efftail" ;;
        w1*) MODEL_DIR="$SWIFTDIR"; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0 ;;
        o1rm) MODEL_DIR="$(pack_dir Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5)"; MODEL_REV="${MODEL_DIR##*-}" ;;
        s1m) MODEL_DIR="$(pack_dir scottlowry-Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp-e8ed008)"; MODEL_REV="${MODEL_DIR##*-}" ;;
      esac
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      unset QWEN38_MLX_PLE_GPU QWEN38_MLX_PREFIX_CACHE_MEM QWEN38_MLX_KV_QUANT QWEN38_MLX_CONFIG_OVERRIDES QWEN38_MLX_DRAFTER QWEN38_MLX_DRAFT_BLOCK_SIZE QWEN38_MLX_PREFIX_CACHE_DISK QWEN38_MLX_PREFIX_CACHE_ENTRIES
      case "$CAND" in
        w1c8|w1xc8) export QWEN38_MLX_PREFIX_CACHE_MEM=8GB; REV="${REV}-pc8" ;;
        w1p8|w1xp8) export QWEN38_MLX_PREFIX_CACHE_MEM=8GB QWEN38_MLX_PLE_GPU=1; REV="${REV}-pc8-plegpu" ;;
        n2xd) export QWEN38_MLX_EXTRA_ARGS="${FLASHNEXT_MTP_DEPTH_FLAG:?n2xd needs FLASHNEXT_MTP_DEPTH_FLAG} ${FLASHNEXT_MTP_DEPTH:?n2xd needs FLASHNEXT_MTP_DEPTH}"
              REV="${REV}-mtpd${FLASHNEXT_MTP_DEPTH}" ;;
      esac
      if [[ -n "$YARN" ]]; then
        export QWEN38_MLX_KV_QUANT=8
        export QWEN38_MLX_CONFIG_OVERRIDES="{\"text_config\":{\"rope_parameters\":{\"rope_type\":\"yarn\",\"factor\":${YARN},\"original_max_position_embeddings\":262144},\"max_position_embeddings\":${CTX}}}"
        REV="${REV}-yarn${YARN}-kv8"
        if [[ "$CAND" == w1q4 || "$CAND" == w1xq4 ]]; then export QWEN38_MLX_KV_QUANT=4; REV="${REV%-kv8}-kv4"; fi
      fi ;;
  o1x|o1r|x1)
      # flashnext-next-steps-2026-10 on oMLX 0.7.1.dev2 (isolated venv): o1x = Jundot oQ4e 2615fc0 (launcher arm FN),
      # o1r = Jundot oQ4e refit c4ddfb5 (FR), x1 = umixer oQ4e-mix6-mtp v2 (FM). FR and FM enter
      # config/omlx-arms.json after each download (Tasks 5 and 7 of the campaign plan). umixer retired the -v2 repo
      # on 2026-10-14; the same bytes live in the original repo id at 73d2cd0.
      LAUNCHER="$HARNESS/run-omlx.sh"; PORT=8000; RUNTIME=omlx; REV=v0.7.1.dev2
      case "$CAND" in
        o1x) ARM=FN; MODEL_DIR="$OQ4E" ;;
        o1r) ARM=FR; MODEL_DIR="$(pack_dir Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-c4ddfb5)" ;;
        x1) ARM=FM; MODEL_DIR="$(pack_dir umixer-Qwen3.8-Flash-Next-oQ4e-mix6-mtp-73d2cd0)" ;;
      esac
      MODEL_REV="${MODEL_DIR##*-}"
      TOKENIZER="$MODEL_DIR"; METRICS=""; SERVER_NAME=omlx
      PROBE_PY="$OMLX_0712/bin/python"
      export OMLX_MODEL_ROOT="$MODEL_ROOT" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_OMLX_BIN="$OMLX_0712/bin/omlx" QWEN38_OMLX_EXPECTED_VERSION=0.7.1.dev2 ;;
  g0|g1|g1m)
      # flashnext-next-steps-2026-10, test #8: ggml-org GGUF IQ4_NL + MTP head Q8_0. g0 = llama.cpp b11569 without
      # speculative decoding; g1 = --spec-type draft-mtp; g1m = mlx-serve 26.10.2 (embedded llama.cpp), same files.
      LAUNCHER="$REPO/bench/flashnext-next-steps-2026-10/scripts/run-llama-flashnext.sh"
      MODEL_DIR="$(pack_dir ggml-org-Qwen3.8-Flash-Next-GGUF-)"; MODEL_REV="${MODEL_DIR##*-}"
      TOKENIZER=""; METRICS=""; PROBE_PY=python3
      export QWEN38_GGUF_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      if [[ "$CAND" == g1m ]]; then
        ARM=GX; PORT=11234; RUNTIME=mlx-serve; SERVER_NAME=mlx-serve; REV="v$MLXSERVE_26102_VERSION-gguf"
        export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26102" MLX_SERVE_EXPECTED_VERSION="$MLXSERVE_26102_VERSION"
      else
        PORT=8080; RUNTIME=llama.cpp; SERVER_NAME=llama-server; MODEL_ID_PREF=flashnext-gguf
        export QWEN38_LLAMA_SERVER_BIN="$LLAMA_B11609"
        if [[ "$CAND" == g0 ]]; then ARM=GN; REV=b11609; else ARM=GM; REV=b11609-mtp; fi
      fi ;;
  w1c1|w1c1a|w1c1x2|w1c2|w1c2a|w1c2m8|w1c4|w1c4a|w1c2L|w1c2m4|w1c2q8|w1c2m4q8|w1c2ap3|w1c2ap5|w1c3a)
      # flashnext-concurrency-2026-10: w1 (Swift 1.5 @ 26.10.1) with --max-concurrent N and N parallel
      # cache_probe streams (bench/flashnext-concurrency-2026-10/scripts/run-parallel-probes.sh).
      # "a" = auxiliary load generator on; m8/m4 = prefix cache 8/4 GB; q8 = 8-bit KV;
      # L = asymmetric streams (262144 + 32768). Every 256K arm and w1c2m8 runs with the generator.
      # w1c1x2 = serialized control: 2 streams + generator on one slot (--max-concurrent 1 pinned).
      # w1c3a = 3 streams + generator (user request, 2026-10-18).
      # w1c2ap3/ap5 = w1c2a + --prefill-decode-share 0.3/0.5 (decode keeps that share while another prefills).
      LAUNCHER="$HARNESS/run-mlx-serve.sh"; ARM=FS; PORT=11234; RUNTIME=mlx-serve; REV=v26.10.1
      MODEL_DIR="$SWIFTDIR"; MODEL_REV=13839b7191e0973ff9fea58232267c395b76c6c0
      PROBE_PY=python3; TOKENIZER=""; SERVER_NAME=mlx-serve; METRICS=""
      export QWEN38_MLX_SERVE_BIN="$MLXSERVE_26101" MLX_SERVE_EXPECTED_VERSION=26.10.1
      export QWEN38_MLX_MODEL_DIR="$MODEL_DIR" QWEN38_CTX_SIZE="$CTX"
      export QWEN38_MLX_SSM_CHECKPOINT_MAX="${QWEN38_MLX_SSM_CHECKPOINT_MAX:-16}"
      unset QWEN38_MLX_PLE_GPU QWEN38_MLX_PREFIX_CACHE_MEM QWEN38_MLX_KV_QUANT QWEN38_MLX_CONFIG_OVERRIDES QWEN38_MLX_EXTRA_ARGS
      PAR_N=1; PAR_AUX=""; PAR_CONTEXTS=""
      case "$CAND" in w1c2*|w1c1x2) PAR_N=2 ;; w1c3*) PAR_N=3 ;; w1c4*) PAR_N=4 ;; esac
      MC="$PAR_N"; [[ "$CAND" == w1c1x2 ]] && MC=1
      case "$CAND" in w1c1a|w1c1x2|w1c2a|w1c3a|w1c4a|w1c2m8|w1c2L|w1c2m4|w1c2q8|w1c2m4q8|w1c2ap*) PAR_AUX=1 ;; esac
      [[ "$CAND" == w1c2L ]] && PAR_CONTEXTS="262144,32768"
      case "$CAND" in
        w1c2m8) export QWEN38_MLX_PREFIX_CACHE_MEM=8GB; REV="${REV}-pc8" ;;
        w1c2m4|w1c2m4q8) export QWEN38_MLX_PREFIX_CACHE_MEM=4GB; REV="${REV}-pc4" ;;
      esac
      if [[ "$CAND" == *q8 ]]; then export QWEN38_MLX_KV_QUANT=8; REV="${REV}-kv8"; fi
      if [[ "$PAR_N" -gt 1 ]]; then export QWEN38_MLX_EXTRA_ARGS="--max-concurrent $MC"; REV="${REV}-mc${MC}"; fi
      if [[ "$CAND" == w1c2ap* ]]; then
        PDS="${CAND#w1c2ap}"; QWEN38_MLX_EXTRA_ARGS="$QWEN38_MLX_EXTRA_ARGS --prefill-decode-share 0.$PDS"; REV="${REV}-pds$PDS"
      fi
      ARM_EXEC="bash $REPO/bench/flashnext-concurrency-2026-10/scripts/run-parallel-probes.sh --streams $PAR_N${PAR_AUX:+ --aux}"
      ARM_EXEC="$ARM_EXEC --context $CTX${PAR_CONTEXTS:+ --contexts $PAR_CONTEXTS} --repeat $REPEAT --arm $CAND --tag ${TAG:-untagged}"
      ARM_EXEC="$ARM_EXEC --temperature $TEMP --reasoning-effort $EFFORT --runtime-revision $REV --model-revision $MODEL_REV"
      ARM_EXEC="$ARM_EXEC --out $RESULTS" ;;
  *) echo "candidato desconhecido: $CAND" >&2; exit 64 ;;
esac
# A concurrency arm brings its own probe command; an --exec on the command line still wins.
[[ -z "$EXEC_CMD" && -n "$ARM_EXEC" ]] && EXEC_CMD="$ARM_EXEC"
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
  # --exec troca o probe por outro comando contra o servidor (ex.: bateria de qualidade).
  [[ -n "$EXEC_CMD" ]] && { echo "exec: $EXEC_CMD"; echo "effort: $EFFORT"; echo "saida: $OUT"; exit 0; }
  echo "probe: $PROBE_PY cache_probe.py --base-url $BASE/v1 --runtime $RUNTIME --runtime-revision $REV --context $CTX --repeat $REPEAT --temperature $TEMP ${SCENARIOS:+--scenarios $SCENARIOS} ${TOKENIZER:+--tokenizer-path $TOKENIZER} ${METRICS:+--metrics-url $METRICS} ${SCENARIO_REPEATS:+--scenario-repeats $SCENARIO_REPEATS} ${PROBE_SESSION_HEADER:+--session-header $PROBE_SESSION_HEADER} ${PROBE_PRIME_MAX_TOKENS:+--prime-max-tokens $PROBE_PRIME_MAX_TOKENS} ${QWEN38_PROBE_MAX_TOKENS:+--max-tokens $QWEN38_PROBE_MAX_TOKENS}"
  echo "effort: $EFFORT"
  echo "saida: $OUT"; exit 0
fi
# Um pack ausente ou incompleto faz o servidor morrer no boot com erro pouco claro: recusar antes.
[[ -e "$MODEL_DIR" ]] || { echo "run-candidate: pesos ausentes em $MODEL_DIR" >&2; exit 66; }

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

SERVER_PID=""; SAMPLER_PID=""; SERVER_STARTED=""
cleanup() {
  [[ -n "$SAMPLER_PID" ]] && kill "$SAMPLER_PID" 2>/dev/null || true
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
  # SERVER_PID is the `nohup bash "$LAUNCHER" ...` wrapper, not necessarily the
  # runtime process itself -- kill whatever is actually listening on $PORT too,
  # or a dead probe leaves the server (and the port) held by an orphan.
  # Only when this run started a server: an exit before the boot (port busy) must not
  # kill another session's server (on 2026-10-10 it killed the daily driver's mlx-serve).
  [[ -n "$SERVER_STARTED" ]] || return 0
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
SERVER_STARTED=1; nohup bash "$LAUNCHER" "$ARM" >"$BOOT" 2>&1 & SERVER_PID=$!
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
if [[ -n "$EXEC_CMD" ]]; then
  # O comando recebe o servidor pronto em BASE_URL e MODEL_ID; o código de saída dele vira o do braço.
  BASE_URL="$BASE/v1" MODEL_ID="$MODEL_ID" bash -c "$EXEC_CMD" || PROBE_EXIT=$?
else
"$PROBE_PY" "$HARNESS/cache_probe.py" \
  --base-url "$BASE/v1" --model "$MODEL_ID" --api-model "$MODEL_ID" \
  --runtime "$RUNTIME" --runtime-revision "$REV" --model-revision "$MODEL_REV" \
  --arm "$CAND" --session-id "${TS}-${NAME}" \
  --context "$CTX" --content-class audit_retrieval --repeat "$REPEAT" \
  --temperature "$TEMP" --top-p 0.95 --top-k 20 --reasoning-effort "$EFFORT" \
  ${SCENARIOS:+--scenarios "$SCENARIOS"} \
  ${TOKENIZER:+--tokenizer-path "$TOKENIZER"} \
  ${METRICS:+--metrics-url "$METRICS"} \
  ${SCENARIO_REPEATS:+--scenario-repeats "$SCENARIO_REPEATS"} \
  ${PROBE_SESSION_HEADER:+--session-header "$PROBE_SESSION_HEADER"} \
  ${PROBE_PRIME_MAX_TOKENS:+--prime-max-tokens "$PROBE_PRIME_MAX_TOKENS"} \
  ${QWEN38_PROBE_MAX_TOKENS:+--max-tokens "$QWEN38_PROBE_MAX_TOKENS"} \
  --output "$OUT" --cache-enabled $([[ "$GENMODE" == "" || "$GENMODE" == mtp ]] && echo --mtp-enabled) \
  || PROBE_EXIT=$?
fi

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
