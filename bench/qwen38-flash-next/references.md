# Qwen3.8-Flash-Next (125B-A6B)

> **Status: 🟡 PROMOÇÃO CONDICIONAL.** MoE de geração "Qwen4", mais rápido que a densa 3.8-27B
> e reusa cache melhor, mas não desloca a densa em trabalho de agente sustentado (qualidade).
> Rodado no rig em 2026-08-31 (oMLX 0.6.4, build oQ4e): decode ~40 tok/s @32K, ~33 @128K.
> Fonte da research: notas consolidadas em 2026-08-29 (branch absorvida `worktree-bench+qwen38-flash-next`).

Marcar a procedência de cada número: **fabricante** (Alibaba/Qwen), **terceiro** (card HF / blog / Reddit),
ou **medido-no-rig** (esta campanha, M4 Max 128 GB).

## At a glance (oficial)

| Campo | Valor | Fonte |
|---|---|---|
| Base | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) | HF |
| Parâmetros | 125B totais MoE / ~6B ativos; 512 experts; 48 camadas (+51B tabela n-gram +4B MTP = 177B em disco) | HF / card AtomicChat |
| Arquitetura | `qwen4_exp` (preview Qwen4): Gated DeltaNet + Qwen Sparse Attention + gated residual alargado. **Só 12 de 48 camadas mantêm KV crescente**; o resto é estado fixo do DeltaNet | kaitchup / HF |
| Contexto | **262.144 nativo**; 1.000.000 com YaRN | HF |
| MTP | módulo de 4B embutido (speculative decoding nativo, como os packs MTPLX) | HF |
| Licença | qwen-community (≠ Apache-2.0 da 3.8-27B) | HF |
| Lançamento | 2026-08-26 | — |

**Runtime:** exige suporte a `qwen4_exp` — mlx-lm antigo NÃO carrega. Servem: oMLX (≥0.6.3),
MLX-VLM, builds mlx-serve, MTPLX ≥2.10.0, llama.cpp mainline (PR #27742, merge 2026-08-28).

## Fit no M4 Max 128 GB — a tabela n-gram decide o footprint

A tabela n-gram (~32 GB em 4-bit) é o que estoura a memória. Duas estratégias: residente vs mmap do SSD.

| Build | Disco | n-gram | Residente | Procedência |
|---|---|---|---|---|
| Vontra MLX-4bit (grupo 32) | 112 GB | RAM | apertado | card HF |
| pipenetwork mixed-4/8 | 106 GB | RAM | apertado | card HF |
| **ddalcu MLX-Serve mixed-4/8** | **75 GB** | **mmap SSD** | **~75 GB** | card HF |
| Jundot oQ4e-mtp (oMLX) | 106 GB | — | **99.6 GB (resident) / 69.6 GB (com offload)** | **medido-no-rig** |
| AtomicChat GGUF Q4_K_M | 92.9 GB | mmap SSD | ~65 GB (offload) / 45.8 GB num M5 Max 64 GB | terceiro |

**Regra de qualidade** (ablação do card pipenetwork): manter os ~4,2B de pesos NÃO-expert em 8-bit
derruba a perda de +20,6% para +1,3% de perplexidade — esses 4B são ~20x mais sensíveis à quantização
que os 121B de experts. **Preferir a receita mixed-4/8**, não 4-bit chapado em atenção/DeltaNet.

## Medido no rig (2026-08-31, oMLX 0.6.4, build Jundot oQ4e-mtp)

⚠️ **Config crítica:** o setting oMLX **`qwen4_ple_ssd_offload`** vem `False`. Sem ele o oQ4e carrega
**99.6 GB residente** e SATURA os 128 GB (pico 128.9 GB + 6.3 GB swap já a 32K), e o preflight do
memory-guard rejeita o prefill. Com `qwen4_ple_ssd_offload: true` (na arm), o PLE vai para mmap no SSD:
**residente cai para 69.6 GB, swap 0**, e o 128K cabe. Custo: ~15% de decode (paginação do n-gram/PLE).

Com o offload (5 cenários × 1 rep, todos corretos, swap 0):

| Contexto | decode tok/s | cache: identical / append / tool_turn | pico RAM |
|---|---|---|---|
| 32K | ~40 | 0.975 / 0.940 / **0.938** | 113.4 GB |
| 128K | ~33 | 0.995 / 0.986 / **0.986** | 116.9 GB |

- **Mais rápido que as densas:** @32K L(oMLX) 42.5, S(dspark) 41.8, T(oMLX oQ8e) 32.0; @128K densas ~25
  → Flash-Next **+31% a 128K**. Esperado de um MoE A6B.
- **Cache reusa `tool_turn` (0.986 @128K)** — que o session-bank do MTPLX denso NÃO conseguia; o cache
  content-addressed do oMLX resolve.
- **KV pequeno confirmado:** ~27,3 KB/tok (só 12/48 camadas com atenção cheia) → ~6,8 GB a 262K. Por isso
  o contexto longo cabe (ao contrário do 3.8-27B denso, que colapsava). Máx no rig com offload: **256K**
  out-of-the-box; 512K esticado; 1M precisa `sudo sysctl iogpu.wired_limit_mb=...`.

### Medido no rig — build ddalcu MLX-Serve (mlx-serve v26.8.11, 2026-08-31) — O CAMINHO RECOMENDADO

Serve `qwen4_exp` nativo com n-gram **mmapped por design** (log: `n-gram table 320M rows 4-bit mmapped,
PLE at layer 1, QSA budget 2048/4`), MTP forçado ON. **Sem hack de offload, sem swap.** @32K, 5 cenários:

| Cenário | cache hit | decode | prefill |
|---|---|---|---|
| cold | — | 59.6 | 568 |
| identical | 1.000 | 63.7 | 15 (hit) |
| append | 0.000 | 60.7 | 634 |
| middle_mutation | 0.000 | 63.5 | 638 |
| tool_turn | 0.961 | 64.1 | 403 |

- **Decode ~60-64 tps** — ~1,5x o oQ4e no oMLX (~40) e as densas (~32-42). Pico 105.8GB, **swap 0**.
  Não chegou aos ~78 do vendor (aquilo era código + MTP; nosso probe é audit_retrieval → bate o ~60 serial).
- **Cache diferente do oMLX:** reusa `identical` e `tool_turn` (0.961), mas re-prefila `append`/`middle`
  (0.00). Mitigado pelo prefill rápido (~630 tps). O oMLX oQ4e reusava `append` (0.94) mas era mais lento.
**Contexto longo no mlx-serve** (tool_turn como referência de decode+cache; append/middle seguem 0.00):

| Contexto | decode | tool_turn hit | pico RAM | swap |
|---|---|---|---|---|
| 32K | ~60-64 | 0.961 | 105.8GB | 0 |
| 128K | ~44 | 0.991 | 120.5GB | 0 |
| 256K (nativo) | 33.4 (cold) | HTTP 400 (memória) | 119.7GB | 0 |

O mlx-serve mantém a liderança de decode em todo contexto (@128K ~44 vs oQ4e/oMLX ~33; @256K 33.4 vs
oMLX ~27 vs densas ~7-14). Cabe até o máximo nativo (256K, pico 119.7GB, sem swap) para UM request.
**Borda (não bug):** o `tool_turn` @256K faz um segundo request sobre o contexto cheio, e o mlx-serve
o REJEITA com HTTP 400 por memória — log: `prompt 256657 tokens needs ~19950MB (KV+working+margin),
~14751MB available — rejecting`. Com o modelo (~83GB) + KV residente do cold + o cap wired do Metal
(default ~107,5GB), não sobra working memory para um segundo prompt de 256K.

**Soluções testadas (2026-09-01) — 4 knobs, nenhum resolveu:**

| Config | cold | tool_turn @256K | nota |
|---|---|---|---|
| default (kv off, guard 86G, chunk auto 4096) | OK (decode 33.4) | **400** | needs ~19950MB > avail ~14751MB |
| `--kv-quant 8 --kv-attn-mode fused` (+max-resident 0) | OK (decode **20.7 ↓38%**) | **400** | needs ~17052 > avail ~16060 (faltou ~1GB) |
| `--max-resident-mem 0` (guard off) | **Metal OOM hard (crash)** | — | desligar o guard troca o 400 gracioso por crash |
| `--prefill-chunk 2048` (guard on) | **Metal OOM hard (crash)** | — | forçar chunk < auto (4096) PIOROU |

**Diagnóstico:** o `needs` = KV (~5,8GB a 256K) + **working memory do prefill (~14GB, dominante)** + margem.
O kv-quant só encolhe o KV (8-bit −2,9GB; 4-bit −4,35GB), não o working. `--kv-quant 6` NÃO existe no
mlx-serve (opções: 4, 8, turbo2, turbo4). Pela matemática, **kv-quant 4** chegaria a ~15600MB < ~16060
avail → caberia **na margem**, mas mais lento e frágil (não testado). `--max-resident-mem 0` e
`--prefill-chunk` menor **pioram** (OOM hard em vez de refusal). A web confirmava o prefill-chunk como
fix de OOM de prefill longo, mas empiricamente neste build/máquina não ajudou.

**Fix confiável = `sudo sysctl iogpu.wired_limit_mb=124518`** (107,5 → ~119GB): ataca o termo certo
(working memory, +12GB de teto), **sem custo de decode**, com folga real (não na margem). É a config
padrão de contexto longo em Mac 128GB; para permanente, um LaunchDaemon no boot.

**Relevância para uso diário agêntico:** 256K one-shot roda ótimo (decode 33.4). O multi-turn a 256K
aparece SÓ nos workloads de contexto longo pelos quais se escolhe o Flash-Next (>100k, runs autônomos
longos). Nesses, é recorrente — mas o multi-turn REAL cresce incremental e reusa o KV residente (prefila
só o delta), bem mais leve que o `tool_turn` sintético (re-prima 256K inteiro). Ressalva: o mlx-serve
reusa `identical`/`tool_turn` mas re-prefila `append`/`middle`, então turnos que ele não reconhece pagam
re-prefill cheio e batem no teto. Conclusão: se 256K agêntico é o alvo, **subir o wired-limit
permanentemente** é o caminho; senão (uso ≤128K ou 256K one-shot) o 400 não aparece.

- **Veredito:** mlx-serve v26.8.11 + ddalcu é **o caminho recomendado do Flash-Next no rig** — decode mais
  rápido, memória mais limpa (mmap nativo), correto. Dados: `results/flashnext-mlxserve-{32k,128k}-v26811.jsonl`.

**Não medido ainda:** o **Terminal-Bench** (qualidade de agente, do driver) — o gate decisivo.

## As duas quants/builds: características, prós/contras e recomendação

Ambas são MoE 4-bit affine g64 com a mesma ideia central — manter os pesos NÃO-expert (~4B, ~20x mais
sensíveis à quantização) em precisão maior. Diferem na granularidade e, sobretudo, no armazenamento do
n-gram (a decisão que domina o footprint).

| Característica | oQ4e (Jundot / oMLX 0.6.4) | ddalcu mixed-4/8 (mlx-serve 26.8.11) |
|---|---|---|
| Não-expert (atenção/DeltaNet) | 5-6 bit seletivo (181 tensores 5b, 99 6b) | 8-bit chapado ("the rest") |
| Experts | 4-bit base + ~196 tensores 8-bit (gates/router) | 4-bit puro |
| n-gram (51B) | 4-bit DENTRO dos safetensors → residente por default | 4-bit em `ngram_table.bin` (32GB) SEPARADO, mmapped por design |
| Disco / Residente | 106GB / 99.6GB (69.6GB com `qwen4_ple_ssd_offload:true`) | 107GB / ~75-83GB (n-gram sempre no mmap) |
| Decode @32K / @128K | ~40 / ~33 | ~60-64 / ~44 |
| Cache | reusa identical, append (0.94), tool_turn (0.94), middle parcial | reusa identical, tool_turn (0.96-0.99); re-prefila append/middle |

### oQ4e / oMLX — prós e contras
**Prós:** quant mais fino (5/6/8-bit por sensibilidade → qualidade ligeiramente melhor no não-expert);
o cache content-addressed do oMLX reusa `append` (conversa que cresce); ecossistema oMLX (Lightning MTP,
visão, tool calls, warm-prefix restore, spill de KV no SSD).
**Contras:** armadilha de memória — n-gram embutido carrega residente (99.6GB, satura 128GB + swap) a menos
que se ligue o setting não-óbvio `qwen4_ple_ssd_offload:true`; mais lento (~40/33, o offload pagina o
n-gram, ~15%); prefill do n-gram no SSD ainda incompleto (oMLX PR #3235 aberta); ~1,5x mais lento no geral.

### ddalcu mixed-4/8 / mlx-serve — prós e contras
**Prós:** mais rápido (~1,5x o oQ4e em todo contexto); memória limpa por design (n-gram mmapped, nunca
residente → cabe até 256K sem swap e sem setting); prefill rápido (~630 tps) compensa cache misses; receita
mixed-4/8 é a validada em qualidade (não-expert 8-bit → só +1,3% de perda); serve simples, MTP forçado on.
**Contras:** cache mais estreito (não reusa `append`/`middle`, só identical+tool_turn — conversa que cresce
paga re-prefill por turno, mitigado pelo prefill rápido); runtime à parte (binário mlx-serve, instalação
separada, menos features verificadas que o oMLX); quant mais grosso (8-bit chapado gasta mais bits que o
5/6-bit fino do oQ4e); menos maduro/testado.

### Recomendação
- **ddalcu / mlx-serve = default no rig:** velocidade, contexto longo, memória folgada, serve simples.
  Ganha para uso geral e agente com contextos grandes distintos.
- **oQ4e / oMLX = quando o padrão é conversa única que cresce** (reuso de `append`), ou se já se está no
  stack oMLX (visão, tool-cache, integração Claude Code), ligando o offload.

**RESSALVA:** a qualidade de agente (Terminal-Bench) NÃO foi medida em nenhum dos dois — os prós de qualidade
acima são inferidos das receitas de quant, não medidos. O veredito de qualidade depende do T-Bench (do driver).
Até lá, a comparação é sólida em velocidade, memória e cache, não em qualidade final.

## Velocidade (terceiros)

- Build MLX-Serve mixed-4/8 (~75 GB), M4 Max: decode ~60 serial / **~78 com MTP**; prefill ~730 tok/s (card ddalcu).
- Contexto longo (GGUF UD-IQ4_XS, Mac 128 GB, heretik.io): decode 33 vazio → **11 a 262K**; encher 262K ~28 min; KV 6,4 GB.
- oMLX no M4 Max (u/tolitius, 27/ago): prefill **~2,5x mais rápido que o 27B** (o A6B alivia o compute-bound do prefill).

## Qualidade (TODOS do fabricante, salvo nota — sem replicação independente sólida)

| Benchmark | Flash-Next | Opus 4.6 Max |
|---|---|---|
| SWE-bench Pro | 62,5 | 53,4 |
| CoWorkBench | 73,9 | 68,2 |
| JobBench | 55,7 | 36,6 |
| Humanity's Last Exam | 35,9 | **40,0** |

Bate o 3.8-27B denso em todos os benchmarks publicados; maiores folgas em coding agêntico de longo
horizonte, uso de ferramentas e transcrições >100k. **Fraqueza declarada: fragilidade em cadeias de
agente muito longas** ("promete o entregável, declara 'done', não gera nada" — teste próprio NVFP4-vs-densa).

**Ceticismo (comunidade):** os benchmarks de quant "really good" (AtomicChat) usam 1 juiz LLM + ~66 tarefas
→ ruidoso; servem para comparar quants do MESMO modelo, não como leaderboard. Sinal independente positivo:
no Aider polyglot local (u/returnity), Flash-Next em Q4 domina o 3.8-27B.

## Suporte nos runtimes (2026-08-31)

- **oMLX 0.6.4:** serve `qwen4_exp` nativo, Lightning MTP, **warm-prefix restoration do MTP** (resolve a
  restrição "sem cache, 65K" da 0.6.3rc). Prefill com n-gram no SSD ainda depende de PR aberta ([#3235](https://github.com/jundot/omlx/pull/3235),
  batched prefetch 2,6–4,35x) — por isso o offload custa decode hoje. **Caminho usado nesta campanha.**
- **MTPLX 2.10.0:** família nativa; packs "Bare Speed" e "Optimized Speed"; **n-gram faz stream do SSD →
  cabe em 96 GB**; hot-row cache. A 147K num M5 Max, decode 18,4 tok/s (+54% vs 12,0). Bom caminho para cache.
- **llama.cpp mainline:** `qwen4_exp` desde 2026-08-28 (PR #27742). Offload de n-gram sem repack:
  `--load-mode mmap --override-tensor per_layer_token_embd.weight=CPU`. ~36 tok/s (sem MTP). Lida melhor
  que o oMLX com o offload de n-gram hoje (u/returnity).
- **mlx-dspark 0.17.2:** SEM suporte a `qwen4_exp`. Fora do braço até haver suporte.

## Próximos passos

1. Rodar o build **ddalcu MLX-Serve mixed-4/8** (75 GB, n-gram mmap nativo) — deve dar mais decode e mais
   folga que o oQ4e; comparar com os números medidos acima.
2. **Terminal-Bench** (do driver com Docker) — o gate decisivo de qualidade de agente (foi o NO-GO do 27B).
3. Avaliar MTPLX pack e llama.cpp GGUF como caminhos de cache alternativos.

Empírico desta campanha: `results/refresh-flashnext-*.jsonl` (movidos do smoke R5 do runtime-refresh).
Runbook: [plan.md](plan.md). O smoke R5 original: `../qwen3.8-prefix-cache/plan-runtime-refresh.md` (seção R5, agora um ponteiro).
Memória: [qwen38-flash-next-stacks].

## Fontes

- Review/arquitetura: https://kaitchup.substack.com/p/qwen38-flash-next-review-benchmarks · https://www.datacamp.com/blog/qwen3-8-flash-next
- Builds: [ddalcu MLX-Serve 75GB](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit) · [Vontra 4bit](https://huggingface.co/Vontra/Qwen3.8-Flash-Next-MLX-4bit) · [pipenetwork mixed-4/8](https://huggingface.co/pipenetwork/Qwen3.8-Flash-Next-MLX-mixed-4_8bit) · [Jundot oQ4e (usado)](https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp) · [AtomicChat GGUF](https://huggingface.co/AtomicChat/Qwen3.8-Flash-Next-GGUF)
- Contexto longo num Mac: https://heretik.io/qwen38-flash-next-262k-macbook/
- Reddit: [AtomicChat GGUF](https://www.reddit.com/r/LocalLLaMA/comments/1w17zbg/atomicchatqwen38flashnextgguf_is_really_good/) · [n-gram SSD offload llama.cpp](https://www.reddit.com/r/LocalLLM/comments/1vz927j/got_qwen38nextflash_ngram_ssd_offload_working_in/) · [benchmarks M4 Max](https://www.reddit.com/r/LocalLLaMA/comments/1vzspz6/qwen38flashnext_time_to_update_those_benchmarks/)
- Runtimes: [llama.cpp PR #27742](https://github.com/ggml-org/llama.cpp/pull/27742) · [oMLX #3235](https://github.com/jundot/omlx/pull/3235) · [MTPLX Flash-Next pack](https://huggingface.co/Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed)
- NVIDIA GB300: https://developer.nvidia.com/blog/experiment-with-qwen3-8-flash-next-on-nvidia-gb300-nvl72-for-agentic-coding/
