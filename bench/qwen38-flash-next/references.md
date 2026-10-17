# Qwen3.8-Flash-Next (125B-A6B)

> **Status: 🟡 PROMOÇÃO CONDICIONAL.** MoE de geração "Qwen4", mais rápido que a densa 3.8-27B
> e reusa cache melhor, mas não desloca a densa em trabalho de agente sustentado (qualidade).
> **Drivers do rig (confirmados em 2026-10-16), ambos no mlx-serve 26.10.1** (`--mtp`, prefix-cache 16GB/100GB/64):
> **principal** Swift 1.5 (`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` `13839b7`), T_turno 7.9 / 8.6 s a
> 32K / 128K; **secundário** ddalcu iQ-MLX-4.7bpw (`dafff5c`, HEAD no HF em 12/10), T_turno 8.1 / 8.9 s, com
> 256K (9.8 s) e 512K (13.0 s, `--kv-quant 4` + YaRN 2.0) medidos. O perfil `512k` usa o Swift desde 14/10
> (13.3 s, needles 13/13). O mlx-serve 26.10.2 não foi adotado (1.038× / 1.000× do 26.10.1 a 32K / 128K).
> Card do driver: [docs/models/qwen3.8-flash-next.md](../../docs/models/qwen3.8-flash-next.md). Campanhas:
> [flashnext-next-steps-2026-10](../flashnext-next-steps-2026-10/results/summary.md) (16–17/10, drivers e runtime mantidos; effort `xhigh` fixo por sessão, `medium` só em chat e tool-calling curtos, Swift aprovado a 256K com needles 26/28; o template com o effort no fim do prompt resolve a troca de effort, mas perde o cache em prompts curtos e não vira default),
> [swift15-flashnext-2026-10](../swift15-flashnext-2026-10/results/summary.md) (11/10, Swift vence o iQ),
> [engine-updates-2026-10](../engine-updates-2026-10/results/flashnext-summary.md) (26.10.1, oMLX 0.7.0, MTPLX, 512K),
> [qwen38-flashnext-daily-driver-2026-09](../qwen38-flashnext-daily-driver-2026-09/plan.md).
> Histórico: driver de 2026-09-13 era o ddalcu mixed-4/8 no 26.9.2 (decode 67/58/57 tok/s a 32K/128K/262K, 51 tok/s a 512K;
> [flashnext-stacks-summary.md](../qwen38-updates-2026-09/results/flashnext-stacks-summary.md)); o pack foi apagado em 10/10.
> Plano de 12/10: [research/qwen38-flashnext-next-steps-20261012.md](../../research/qwen38-flashnext-next-steps-20261012.md);
> executado na campanha flashnext-next-steps-2026-10 (Terminal-Bench segue adiado).
> Primeira medição no rig em 2026-08-31 (oMLX 0.6.4, build oQ4e): decode ~40 tok/s @32K, ~33 @128K.
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

> **Fechamento 2026-09-13 (mlx-serve 26.9.2, campanha `qwen38-updates-2026-09`).** A tabela acima é do
> v26.8.11; o 26.9.2 (promovido, A/B limpo vs 26.9.1: +7% @32K, +20–40% @128K) muda o quadro:
>
> | Contexto | decode | prefill | cold TTFT | cache (identical/tool_turn) | wired | kv-disk |
> |---|---:|---:|---:|---|---:|---:|
> | 32K | 67.1 | 732 | 37 s | 1.00 / 0.96 | ~105 GB | 0 |
> | 128K | 57.8 | 703 | 179 s | 1.00 / 0.99 | ~105 GB | — |
> | 262K (nativo) | 56.8 | 676 | 380 s | 1.00 / 1.00 | ~105 GB | ~8 GB |
> | 512K (YaRN 2.0, kv8) | 51.4 | 615 | 844 s | 1.00 | 111.4 GB | 19.8 GB |
> | 1M (YaRN 4.0, kv8) | 34.7 | 502 | 2079 s | follow-up **recusado** | 105.2 GB | 26.5 GB |
>
> Decode quase plano de 32K a 262K; o 400 da 2ª request a 256K não apareceu com o prefix-cache em
> disco (a KV longa spilla para `~/.mlx-serve/kv-cache` por design; swap ~1.7 GB constante). **Teto
> prático = 512K.** 1M é one-shot cold (kv8) ou multi-turno a ~5 tok/s (`turbo4`) — nicho, fora do
> uso diário. ds4 (fork ivanfioravanti): footprint 80–88 GB, mas decode 40/39/36 e prefill ~575 —
> perde em tudo no M4 Max; cache só com `--kv-disk-dir`. MTPLX 2.11.2 promovido por correção (a MTP
> da 2.11.1 é lossy a 32K na densa 27B). oMLX 0.7.0.dev2 deferida aqui, depois medida
> na campanha do driver diário (c3, 2º lugar; PLE offload via `model_settings.json`).
> Dados: `../qwen38-updates-2026-09/results/p1-*.jsonl`, `p4c-*.jsonl`.

> **Atualização 2026-09-07 — o `append`/`middle` a 0.00 era CAP de 2 GB, não design.** A/B no mesmo
> binário v26.9.1, Flash-Next @128K, só a config de prefix-cache mudou (`--prefix-cache-mem/-disk/-entries`):
>
> | Cenário | KNOBS 16GB/100GB/64 | DEFAULT 2GB/off/32 |
> |---|---|---|
> | identical | **1.00 · 0.2s** | 0.00 · 183.7s |
> | append | **0.99 · 2.2s** | 0.00 · 185.1s |
> | tool_turn | **0.99 · 2.2s** | 0.58 · 81.3s |
> | middle_mutation | 0.46 · 108.7s | 0.00 · 183.6s |
> | decode médio | 44.6 tok/s | 43.5 tok/s |
>
> O default de 2 GB não cabe um prefixo de 128K (~3.7 GB): a resposta traz `static_prefix_prior_match:true`
> mas `cache_hit_ratio:0.0` (casa, mas não retém). 16 GB retém → identical/append/tool_turn ~2 s, custo zero
> de decode. Ou seja, o mlx-serve **reusa `append` a 128K** com o cap adequado; só o `middle_mutation` fica
> parcial (0.46, intrínseco à mutação do miolo). Isso corrige a caracterização acima ("re-prefila
> append/middle") — era o cap, não design. Dados: `bench/qwen3.8-prefix-cache/results/knob-ab-128k-*.jsonl`;
> fixado no `run-mlx-serve.sh` (arm FS). **Driver principal em uso e teste hoje: Flash-Next ddalcu no
> mlx-serve 26.9.1 @128K, `--mtp` + prefix-cache 16GB/100GB/64.**

> **Concorrência 2026-09-08 — batched decode NÃO engaja no Flash-Next (MoE); execução serial, limite 1.**
> Teste no rig (v26.9.1, servidor no ar): 1 request = 4.7s / decode 106.6 tok/s; 4 requests concorrentes =
> escada 3.6 / 7.2 / 10.8 / 14.4s, cada stream com decode **cheio** (113.7 tok/s) e **zero** eventos
> `[batched] slots=N`. Com `MLX_SERVE_FORCE_BATCHED=1` + `MLX_SERVE_MOE_BATCHED_DECODE=1` o servidor loga
> `force_batched=on — single-slot ticks will route through batched kernel`: troca o kernel de UM slot, não roda
> vários juntos. O batched decode multi-request da changelog (2.76× em 4 streams) é dos trunks **densos**
> Qwen 3.5/3.6/3.8; o `qwen4_exp` (MoE) mantém 1 slot — a especulação MoE (MTP) ocupa o slot único.
> Consequência p/ OpenCode: rodar N agentes em paralelo **não soma throughput** (enfileiram); concorrência
> real de decode exige um modelo denso. Distinto do outro sentido de "concorrente": sessões **quentes no
> cache** (`--prefix-cache-entries`, hoje 64) — essas sim são configuráveis dentro do orçamento de memória
> (16GB RAM / 100GB SSD): ~4 sessões de 128K na RAM, dezenas em contextos típicos de OpenCode (20–40K).

O mlx-serve mantém a liderança de decode em todo contexto (@128K ~44 vs oQ4e/oMLX ~33; @256K 33.4 vs
oMLX ~27 vs densas ~7-14). Cabe até o máximo nativo (256K, pico 119.7GB, sem swap) para UM request.
**Borda (não bug):** o `tool_turn` @256K faz um segundo request sobre o contexto cheio, e o mlx-serve
o REJEITA com HTTP 400 por memória — log: `prompt 256657 tokens needs ~19950MB (KV+working+margin),
~14751MB available — rejecting`. Com o modelo (~83GB) + KV residente do cold + o cap wired do Metal
(default ~107,5GB), não sobra working memory para um segundo prompt de 256K.

**Soluções testadas (2026-09-01) — 5 knobs, nenhum resolveu:**

| Config | cold (decode) | tool_turn @256K | nota |
|---|---|---|---|
| default (kv off, guard 86G, chunk auto 4096) | OK (33.4) | **400** | needs ~19950MB > avail ~14751MB |
| `--kv-quant 8 --kv-attn-mode fused` (+max-resident 0) | OK (**20.7 ↓38%**) | **400** | needs ~17052 > avail ~16060 (faltou ~1GB) |
| `--kv-quant turbo4 --kv-attn-mode auto` | OK (**~11.4 ↓66%**) | **Metal OOM hard (crash)** | guard ADMITIU (KV 4-bit menor) → execução estourou → servidor morreu |
| `--max-resident-mem 0` (guard off) | **Metal OOM hard (crash)** | — | desligar o guard troca o 400 gracioso por crash |
| `--prefill-chunk 2048` (guard on) | **Metal OOM hard (crash)** | — | forçar chunk < auto (4096) PIOROU |

**Diagnóstico:** o `needs` = KV (~5,8GB a 256K) + **working memory do prefill (~14GB, dominante)** + margem.
O kv-quant só encolhe o KV (8-bit −2,9GB; 4-bit −4,35GB), não o working. `--kv-quant 6` NÃO existe no
mlx-serve (opções: 4, 8, turbo2, turbo4). O **turbo4** (4-bit Hadamard-rotated) foi testado a 256K: cold +
identical + append + middle_mutation passaram com needles `{10,50,90}` OK, mas o `tool_turn` deu **Metal
OOM hard (crash do servidor)**, não o 400 gracioso — o KV 4-bit menor fez o guard **admitir** o pedido, aí
a execução real (working ~14GB) estourou o cap. Pior ainda: decode caiu para ~11–13,5 tok/s (−66% vs
default; turbo não aceita `--kv-attn-mode fused`, só `auto`/`dense`). Ou seja, encolher o KV é a alavanca
errada: `--max-resident-mem 0`, `--prefill-chunk` menor e `turbo4` todos **pioram** (OOM hard em vez de
refusal). A web citava prefill-chunk como fix de OOM de prefill longo, mas empiricamente aqui não ajudou.

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

### Fidelidade por bpw — compilação PPL/KLD dos quants GGUF/EXL3 (Reddit, 2026-09-11)

Fonte: u/Right-Band3478, [r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1wdjso1/accuracy_of_qwen38_flash_next_quants_a_compilation/).
Compilação (com IA) dos PPL Δ% e KLD absolutos **publicados nos cards HF** por Unsloth, AesSedai,
Agentonai, AtomicChat e turboderp (EXL3). O eixo x é o "backbone" em GiB (exclui a tabela n-gram).
Traces diferentes foram normalizadas pelo autor; ele não rodou nada. Lido dos gráficos (±10%).

| Faixa | Exemplo | Backbone | PPL Δ% | KLD |
|---|---|---:|---:|---:|
| < 4 bpw | UD-IQ1_M / AD-3.84 / IQ2_S / IQ3_S | 42–52 GiB | 6–10 | 0.16–0.30 |
| ~4.3 bpw (joelho) | AtomicChat AD-4.27 Q4_K_M, EXL3 3.05 | 44–51 GiB | 2.6 | 0.085 |
| ~4.5–5 bpw | UD-IQ4_XS, AD-5.00 Q5_K_M, EXL3 4.05 | 52–60 GiB | 1.2–2.6 | 0.04–0.08 |
| ~4.8–5.5 bpw | UD-Q4_K_XL, Q4_K_M, AP-Q5_K_XL | 75–85 GiB | 0.3–0.9 | 0.025–0.045 |
| ≥ 5.5 bpw | Q5_K_M, UD-Q5/Q6_K_XL, Q8_0 | 100–128 GiB | ≤ 0.3 | ≤ 0.03 |

O que isso diz para o rig (leitura própria):

1. **O joelho da curva fica em ~4.0–4.3 bpw.** Abaixo, a perda cresce rápido (IQ3 ~6%, IQ2 ~10%).
   Acima de ~4.3 a curva é quase plana: de 4.3 para 5.5 bpw ganha-se ~2 pp de PPL e ~0.05 de KLD ao
   custo de +30 GiB. Os nossos três quants MLX (ddalcu mixed-4/8, Jundot oQ4e, MTPLX Optimized-Speed)
   ficam todos na parte plana, em ~4.5–5.5 bpw efetivos. **Fidelidade não deve ser o que os separa;
   responsividade é o eixo certo para escolher entre eles.**
2. **Quantizar a tabela n-gram/PLE para 4-bit custa pouco.** As variantes `(Q4PLE)` da AesSedai ficam
   +0.2–0.3 pp de PPL e +0.005 de KLD acima das irmãs com PLE cheia. Sustenta a receita ddalcu (n-gram
   4-bit em mmap) e o offload do oQ4e: a memória vem de graça em fidelidade.
3. **Não descer abaixo de ~4 bpw para caber.** Um 3-bit ou um REAP/podado para ganhar folga de KV a
   256K+ paga 6–10% de PPL. A alavanca de memória certa é o offload do n-gram e o `iogpu.wired_limit_mb`.
4. **Fallback GGUF com melhor fidelidade por GiB:** AtomicChat AD-4.27 Q4_K_M está na fronteira
   (2.6% / 0.085 a 51 GiB). Continua fora da campanha de responsividade (sem MTP), mas é o candidato
   se a memória virar o bloqueio. O EXL3 não roda em Mac.
5. **Falha de needle na campanha aponta para runtime, não para o quant.** A ≥4.3 bpw todos os quants
   passam retrieval simples; um needle errado na Etapa A é sintoma de MTP lossy ou de cache, como o
   caso MTPLX 2.11.1.

**Limites:** nenhum quant MLX está no gráfico. A quantização afim do MLX (grupo 64, sem imatrix)
não é o K-quant nem o IQ do llama.cpp; a mesma bpw pode dar KLD diferente. Os packs Jundot (oQe) e
MTPLX publicam KLD nos cards — compilar os três MLX na mesma tabela é um item da campanha
[qwen38-flashnext-daily-driver-2026-09](../qwen38-flashnext-daily-driver-2026-09/plan.md). PPL/KLD
não medem qualidade de agente: o MiniMax IQ2_M empatou com o Q3_K_S no Terminal-Bench.

## Suporte nos runtimes (2026-09-13)

- **mlx-serve 26.9.2 (default do rig):** `qwen4_exp` nativo, n-gram mmapped por design, MTP, prefix-cache
  em RAM + disco (`--prefix-cache-mem/-disk/-entries`), YaRN via `--config-overrides`, `--max-mtp-ctx`,
  `--kv-quant {4,8,turbo2,turbo4}`. Batched decode **não** engaja no MoE (1 slot). Ganhos NAX são de M5.
- **oMLX 0.6.4 (estável):** `qwen4_exp` nativo, Lightning MTP, warm-prefix restoration. Flash-Next só cabe
  com `qwen4_ple_ssd_offload: true` (residente 99.6 → 69.6 GB; custo ~15% de decode). @262K: 27 tok/s,
  prefill 217. **0.7.0.dev2 (pré-release):** declara +8–20% de prefill com PLE via SSD. Medida no rig
  em 2026-09-13 (c3): `T_turno` 13.48 / 15.03 s a 32K / 128K, 2º atrás do mlx-serve; PLE offload via
  `qwen4_ple_ssd_offload: true` no `model_settings.json`
  ([summary](../qwen38-flashnext-daily-driver-2026-09/results/summary.md)). O bloqueio de
  [p4-item4](../qwen38-updates-2026-09/results/p4-item4-omlx-dev2-blocked.md) não se confirmou.
- **MTPLX 2.11.2 (default do rig):** pack `Youssofal/Qwen3.8-Flash-Next-MTPLX-Optimized-Speed` (112 GB,
  em disco, nunca medido no rig). Notas da 2.10: n-gram faz stream do SSD, hot-row cache. 2.11.2 corrige a
  MTP lossy da 2.11.1 e recusa antes do swap em 128 GB; verify de flash-decoding gated a M5.
- **ds4 (fork ivanfioravanti, branch `qwen3.8-flash-next`):** roda com `ds4-server` + `--ple` sidecar;
  perde em decode/prefill para o mlx-serve ([p4b](../qwen38-updates-2026-09/results/p4b-ds4-blocked.md)).
- **llama.cpp mainline:** `qwen4_exp` desde 2026-08-28 (PR #27742). Offload de n-gram sem repack:
  `--load-mode mmap --override-tensor per_layer_token_embd.weight=CPU`. ~36 tok/s (sem MTP).
- **mlx-dspark 0.18.0:** SEM suporte a `qwen4_exp`. Fora do braço até haver suporte.

## Próximos passos

1. ~~Rodar o build ddalcu MLX-Serve mixed-4/8~~ — feito (31/08 → 13/09): é o driver do rig.
2. **Terminal-Bench** (do driver com Docker) — o gate decisivo de qualidade de agente. Ainda não rodou.
3. ~~Avaliar MTPLX pack e llama.cpp GGUF como caminhos de cache~~ → virou a campanha
   [qwen38-flashnext-daily-driver-2026-09](../qwen38-flashnext-daily-driver-2026-09/plan.md): driver
   mais responsivo entre ddalcu/mlx-serve, oQ4e/oMLX 0.6.4, oQ4e/oMLX 0.7.0.dev2 e MTPLX pack.
   GGUF fica fora (sem MTP).
   **Atualização (2026-10-09):** o llama.cpp upstream tem MTP para `qwen4exp` desde a PR #29761 (01/10), e o
   mlx-serve 26.10.1 carrega GGUF Flash-Next pelo engine llama.cpp. A premissa "sem MTP" caiu.
   **Medido em 14/10** ([etapa8-gguf.md](../flashnext-next-steps-2026-10/results/etapa8-gguf.md)): `ggml-org` IQ4_NL + MTP Q8_0 no llama.cpp b11609
   decodifica 52.1 tok/s a 32K (36.0 sem MTP), abaixo do smoke de 70. O GGUF não é candidato a driver neste rig.
   Ver [research/qwen38-flashnext-derivatives-20261009.md](../../research/qwen38-flashnext-derivatives-20261009.md).
4. **Pesos novos para testar (lista de 2026-10-10, revisada em 2026-10-12).** Ordem de prioridade. Detalhes e braços em
   [research §11.5](../../research/qwen38-flashnext-derivatives-20261009.md#115-plano-de-teste-proposto-não-executado).
   A revisão de 12/10 e o plano completo (runtime 26.10.2-pre, Swift a 512K, bateria agêntica) estão em
   [research/qwen38-flashnext-next-steps-20261012.md](../../research/qwen38-flashnext-next-steps-20261012.md).
   Resultado (16/10): [flashnext-next-steps-2026-10/results/summary.md](../flashnext-next-steps-2026-10/results/summary.md). Rodaram o mlx-serve 26.10.2
   estável, o oMLX 0.7.1.dev2 e o llama.cpp b11609, no lugar das versões do plano.

   | # | Pesos | Runtime | Download | Por quê | Condição |
   |---|---|---|---:|---|---|
   | 4a | [GBP-DE/Qwen3.8-Flash-Next-oQ5e-mtp](https://huggingface.co/GBP-DE/Qwen3.8-Flash-Next-oQ5e-mtp) `75abb40` | oMLX | 128.6 GB | A/B de qualidade contra o Jundot oQ4e no mesmo runtime. Pack oQ5e mais citado no r/oMLX; o card relata menos loops. | **Substituído em 12/10** pelo umixer oQ4e-mix6 v2 (teste #7 do plano de 12/10). O oMLX 0.7.x recusou um oQ5e num M4 Max 128 GB ([jundot/omlx#4349](https://github.com/jundot/omlx/issues/4349)). **Teste #7 feito em 16/10:** o mix6 não substitui o refit ([etapa7-mix6.md](../flashnext-next-steps-2026-10/results/etapa7-mix6.md)); ver 4e. |
   | 4b | [Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw](https://huggingface.co/Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw) `13839b7` | mlx-serve 26.10.1 | 106.8 GB | Único candidato novo a driver: mesmo layout e runtime do n2, e o card declara 63% menos thinking tokens. | **Feito em 11/10: venceu e é o driver principal** ([swift15 summary](../swift15-flashnext-2026-10/results/summary.md)). Licença aprovada em 10/10. **256K e 512K medidos em 14/10** ([etapa2-swift-long.md](../flashnext-next-steps-2026-10/results/etapa2-swift-long.md)): 512K com KV 4-bit passa todos os gates (13.3 s, needles 13/13, livre mínimo 0.01 GB) e vira o pack do perfil `512k`; 256K com KV sem quantização erra needles em 2 de 13 registros (11.1 s). |
   | 4c | [scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp](https://huggingface.co/scottlowry/Swift1.5-Qwen3.8-Flash-Next-oQ4e-mtp) `e8ed008` | oMLX ou mlx-serve 26.10.2 | 106.3 GB | Swift 1.5 no oMLX. Variante sem `-fp16`, porque o M4 Max tem bf16. | Condição "4b ganhar" atingida em 11/10. **Nova condição (12/10)**: rodar só se o teste #5 (Jundot refit) mostrar um pack oMLX a ≤ 1.03× do Swift no mlx-serve. O pack é anterior ao refit. **Não rodou (15/10):** condição do teste #5 não atingida; o `o1rm` ficou a 1.075× / 1.046× do Swift ([etapa6-scottlowry.md](../flashnext-next-steps-2026-10/results/etapa6-scottlowry.md)). |
   | 4d | [Jundot/Qwen3.8-Flash-Next-oQ4e-mtp](https://huggingface.co/Jundot/Qwen3.8-Flash-Next-oQ4e-mtp) `c4ddfb5` (re-quantizado com oQe refit em 11/10) | oMLX 0.7.1.dev1 ou mlx-serve 26.10.2-pre | 106.3 GB | O card declara KLD contra BF16 0.0877→0.0776 em código (−11.6%) e 0.1909→0.1713 em prosa (**terceiro**). | **Obsoleta a reconversão local de ~354 GB.** Teste #5 do plano de 12/10. Registrar a linha `Qwen4-Exp PLE forced to SSD` no `server.log`. **Feito em 15–16/10** ([etapa5-refit.md](../flashnext-next-steps-2026-10/results/etapa5-refit.md)): no mlx-serve 26.10.2 o refit fica a 1.075× / 1.046× do Swift e erra needles a 128K (12/13), então não vira driver. No oMLX 0.7.1.dev2 tem a mesma velocidade do `2615fc0`, e a mesma qualidade: Veerman 7/12 contra 10/12 na rodada 1 e 9/12 contra 8/12 na rodada 2 (16/24 contra 18/24, ruído). Com o `2615fc0` apagado em 16/10, o refit fica como pack do oMLX. O ganho de KLD (**terceiro**) não aparece na bateria. |
   | 4e | [txgsync/Qwen3.8-Flash-Next-Dynamic-oQ5e-BF16-PLE-mtp](https://huggingface.co/txgsync/Qwen3.8-Flash-Next-Dynamic-oQ5e-BF16-PLE-mtp) `b62713a` | oMLX | 187.4 GB | Feito para M4 Max 128 GB: tabela n-gram, MTP e atenção em alta precisão. | **Substituído em 12/10** pelo umixer oQ4e-mix6 v2 (teste #7), que a comunidade relata acima do oQ5e com ~9 GB a menos (**terceiro**, sem KLD). **Teste #7 feito em 16/10** ([etapa7-mix6.md](../flashnext-next-steps-2026-10/results/etapa7-mix6.md)), com `umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp` `73d2cd0` (mesmos bytes do `-v2`, aposentado): G1 passa em todas as suítes contra o refit, mas nenhuma suíte fica acima da margem; wired +7.6 GB a 256K, swap 0. Não substitui o refit. |
   | 4f | [ISTA-DASLab GSQ-RCO IQ3_S](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) | mlx-serve (engine llama.cpp) ou llama.cpp ≥ b11569 | 83.6 GB | Libera memória (KV de 512K ou um segundo modelo). | Só se a meta for memória, não qualidade. O primeiro GGUF a testar é o `ggml-org` IQ4_NL + cabeça MTP Q8_0 (teste #8 de 12/10), com smoke de decode ≥ 70 tok/s a 32K. **Smoke falhou em 14/10** ([etapa8-gguf.md](../flashnext-next-steps-2026-10/results/etapa8-gguf.md)): 52.1 tok/s no llama.cpp b11609. O GSQ-RCO não foi testado. Os pesos GGUF (99 GB) foram apagados do rig em 16/10. |

   Fora da lista: `mlx-community/…-oQ6e-mtp` (150.5 GB, grande demais para uso diário), variantes `-fp16`,
   packs podados (REAP, Coder), quants abaixo de ~4 bpw, `ben0112/…-oQ4e-mtp` (mesmo quantizador do Jundot)
   e builds abliterated (ver [backlog-uncensored-models.md](../../docs/superpowers/plans/backlog-uncensored-models.md)).

   **Disco do rig (limpeza de 2026-10-10):** de 37 GiB para 918 GiB livres (50% usado). Saíram os caches de
   KV em SSD dos `logs/` das campanhas (subpastas `cache/` do oMLX e `ssd-session-cache/` do MTPLX; os
   `server.log`, `crash.log`, `stats.json`, settings e `flight.jsonl` ficaram), `~/.ds4/engine-updates-kv/`,
   o GGUF do ds4 upstream (reprovado no gate de decode), o ivanfioravanti DS4-Q4 (fork de setembro) e o
   ddalcu mixed-4-8bit (rollback descontinuado; a tabela n-gram segue no pack iQ). Ficaram o ARC4NUM
   Uncensored, o DeepSeek-V4-Flash 0731 do LM Studio, o Jundot oQ4e (base de 4a) e o Youssofal MTPLX.
   Com o mixed-4-8bit e o GGUF do ds4 fora, os braços c1 e d1 de `run-candidate.sh` precisam de novo
   download para rodar.

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
