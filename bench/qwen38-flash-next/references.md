# Qwen3.8-Flash-Next (125B-A6B)

> **Status: 🟡 PROMOÇÃO CONDICIONAL.** MoE de geração "Qwen4", mais rápido que a densa 3.8-27B
> e reusa cache melhor, mas não desloca a densa em trabalho de agente sustentado (qualidade).
> **Driver do rig (2026-09-13): ddalcu mixed-4/8 no mlx-serve 26.9.2**, `--mtp` + prefix-cache
> 16GB/100GB/64 — decode 67/58/57 tok/s a 32K/128K/262K, cache reusa em todo o range, YaRN a 512K
> (51 tok/s). Fechamento em
> [../qwen38-updates-2026-09/results/flashnext-stacks-summary.md](../qwen38-updates-2026-09/results/flashnext-stacks-summary.md).
> Campanha seguinte (driver mais responsivo, quants × runtimes):
> [../qwen38-flashnext-daily-driver-2026-09/plan.md](../qwen38-flashnext-daily-driver-2026-09/plan.md).
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
