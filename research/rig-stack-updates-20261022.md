# Stacks do rig: o que mudou entre 19 e 22/10/2026

O **mlx-serve 26.10.3** (22/10) corrige a #912. A #912 era o motivo de o driver diário ficar fixo na 26.10.1, então a fixação pode ser reavaliada. A troca ainda pede o probe de tool calls e o `T_turno` no rig. Cinco runtimes lançaram versão nova: mlx-serve 26.10.3, oMLX 0.7.1 e 0.7.2, Splash 1.4.0, llama.cpp b11827 e Ollama 0.40.8. A Qwen não mexeu em nenhum modelo. O pack GGUF da ggml-org ganhou sidecars DFlash2, e dois packs novos de Flash-Next cabem em 128 GB. Os testes que saem desta nota estão em [`bench/stack-updates-2026-10/plan.md`](../bench/stack-updates-2026-10/plan.md).

**Procedência.** A nota junta três buscas na web de 22/10, pela API do GitHub, pela API do Hugging Face, pelo PyPI e pelo Reddit. A linha de base é [`rig-stack-updates-20261019.md`](rig-stack-updates-20261019.md). As releases do mlx-serve, do oMLX e do Splash, o fechamento da #912, os assets e as datas das PRs #30795 e #30927 foram conferidos direto na API do GitHub. As marcas seguem a nota de 19/10: **fabricante** é a Qwen, **terceiro** cobre release, issue, PR, card no HF e Reddit, e **medido-no-rig** vem das campanhas deste repo. Nenhum teste rodou para esta nota. Nenhuma fonte da janela traz número de Flash-Next ou do 27B medido num M4 Max. A busca no Reddit não cobriu os posts de 19 a 21/10, porque o endpoint de busca estava bloqueado.

## Resumo por stack

| Stack | Em 19/10 | Em 22/10 | Impacto no rig |
|---|---|---|---|
| mlx-serve | 26.10.2; #912 aberta | **26.10.3** (22/10); #912 e #928 fechadas | Reavaliar a fixação na 26.10.1 (teste 1) |
| oMLX | 0.7.1rc1 | **0.7.1** (20/10) e **0.7.2** (21/10) | MTP Lightning do Flash-Next com profundidade 1 por padrão; #4561 aberta |
| Splash | 1.3.2; #483 aberta | **1.4.0** (20/10); #483 fechada sem fix | Primeiro Splash com Flash-Next, só em GGUF (teste 5) |
| llama.cpp | b11739, estável v0.7.0 | **b11827**; estável continua v0.7.0 | b11822 corrige qwen4exp com drafter DFlash |
| MLX core | 0.32.4 | 0.32.4 (sem release) | Nenhum |
| mlx-lm | 0.32.2; PR #1788 parada | sem mudança | Nenhum |
| MTPLX | 2.12.2 | sem release; PR #650 corrige a #635 | Continua fora do plano |
| LM Studio | 0.4.26 | sem mudança | Nenhum |
| Ollama | 0.40.6 / 0.40.7-rc0 | **0.40.8** (21/10), **0.40.9-rc2** (22/10) | Ainda sem Flash-Next na biblioteca |
| Modelos Qwen | Flash-Next `de4b8e4` | sem mudança | Nenhum |
| Packs da campanha | ggml-org `92796c0` | ggml-org **`91fb003`**; os outros sem mudança | Sidecars DFlash2 novos |
| Packs novos | — | twyx iQ-MLX-6.6bpw; GSQ-RCO-Coder-MLX | Testes 4 e 6 |
| Harnesses | OpenCode 1.19.3, Hermes 0.22.2, Cline 4.1.25 | OpenCode **1.19.4**, Hermes **0.22.4**, Cline sem mudança | Nenhum |

## Correção à nota de 19/10

A nota de 19/10 diz que o b11738 corrige a corrida `moe_reduce` do Metal. O b11738 é o fix de checkpoint SWA (PR #30666). O fix da corrida é a PR #30795, com merge em 19/10 às 08:55Z, commit `098ce52` (**terceiro**, [PR #30795](https://github.com/ggml-org/llama.cpp/pull/30795)). O primeiro build que contém a PR não foi confirmado. Um build b11822 ou posterior contém as duas correções.

## mlx-serve 26.10.3: a regressão de tool calls tem causa e fix

A **v26.10.3** saiu em 22/10 às 18:29Z, depois da v26.10.3-pre-release.1 de 20/10 (**terceiro**, [release](https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.3)). O asset `mlx-serve-bin-macos-arm64.tar.gz` tem digest SHA256 publicado, então o `install-runtime.sh` aceita a release sem override.

- **#912** fechou em 22/10 com o commit 94670d9. O Crush manda `frequency_penalty: 1`, e a 26.10.2 lia esse valor como `repeat_penalty` 2.0. Com a penalidade, o modelo escrevia a tool call como texto. A 26.10.3 usa a definição aditiva da OpenAI. O mantenedor repetiu o request no Qwen3.8-27B 4-bit e obteve a tool call em 4 de 4 tentativas, sem nomear o chip ([issue #912](https://github.com/ddalcu/mlx-serve/issues/912)). O defeito só aparece com um `frequency_penalty` não nulo. O probe do rig deve testar os dois casos.
- **#928** fechou em 22/10 com o commit 046b647. Sob `qwen4_exp`, a 26.10.2 deixava markup de tool no estilo Anthropic no conteúdo e suprimia a tool call. Uma tool call no formato `<invoke>` agora executa.
- **e6a35b1** (PR #936, 21/10): o leitor da tabela n-gram (PLE) aceita qualquer largura de bits afim. Antes, packs oMLX do Flash-Next com tabela 8-bit g32 falhavam com `EmbeddedPleGeometry`.
- **7e444d8** (PR #883): uma escrita de meta que falha no cache em disco agora libera as fatias de mídia duplicadas.
- A PR #935 (drafter DFlash2 para o Flash-Next) segue aberta.
- Os ganhos de CUDA/DGX Spark (PRs #916, #923, #926) e os números das notas vêm de NVIDIA e de M5 Ultra. Nenhum vale para o M4 Max.
- As issues #844 e #853 não mudaram.

## oMLX 0.7.1 e 0.7.2

A **v0.7.1** saiu em 20/10 (**terceiro**, [release](https://github.com/jundot/omlx/releases/tag/v0.7.1)). As mudanças para o Flash-Next:

- A PR #4648 entrou: o MTP Lightning faz um draft por ciclo por padrão. Uma profundidade máxima adaptativa devolve o comportamento antigo.
- O memory guard não freia mais o prefill com memória livre (PR #4603).
- Os caches do Flash-Next crescem em escada de capacidade (PRs #3963 e #4030).

A **v0.7.2** saiu em 21/10 ([release](https://github.com/jundot/omlx/releases/tag/v0.7.2)):

- O Claude Code não re-prefilla mais a conversa inteira depois de um tool result, porque as notas de sistema ficam no lugar (PR #4712).
- O oMLX serve GGUFs do Flash-Next pelo Splash 1.4.0 (PR #4719). O Q2_0 rodou num M5 Pro 64 GB.
- O prefill do DeepSeek passa a rodar em blocos de 8192 tokens, com 4 a 7 GB a mais de pico a 16K.

A issue **#4561** (Prefill Memory Guard rejeita requests longos num rig de 128 GB) segue aberta, sem atualização desde 16/10. Os números das notas vêm de M3 Ultra, M5 Max e M1 Max.

## Splash 1.4.0: Flash-Next em GGUF

O **Splash 1.4.0** saiu em 20/10 (**terceiro**, [release](https://github.com/incoai/splash/releases/tag/1.4.0)). As PRs #449 a #469 entraram juntas.

- Os GGUFs do Flash-Next carregam com atenção esparsa QSA e um draft DFlash2 escolhido automaticamente. **Checkpoints MLX do Flash-Next ainda não são suportados.**
- Flags novas: streaming de experts e PLE pelo SSD (`--expert-memory`, `--ple-memory`), spill de KV ativo (`--sparse-kv-memory`) e YaRN até 1M (`--max-context 1M`).
- `--verify-rows auto` passa a ser o padrão e pode mudar a saída greedy e com seed.
- Os caches persistentes do 27B e do 35B MLX começam frios uma vez depois do upgrade.

A **#483** fechou em 20/10 como comportamento esperado, sem fix. Para runs reproduzíveis, o mantenedor recomenda `--verify-rows all`, um request por vez e um `cache_salt` por request ([issue #483](https://github.com/incoai/splash/issues/483)). A #471 (Swift 1.5 MLX não carrega) segue aberta.

Números da 1.4.0, nenhum de M4 Max:

| Chip e modelo | Mudança | Resultado |
|---|---|---|
| M5 Pro 64 GB, Flash-Next Q2_0 | base | 95 tok/s de decode; 1312 tok/s de prefill a 32K; TTFT com cache 171 ms |
| M5 Max 36 GB, Flash-Next Q2_0 | verify adaptativo | decode +13 a 38% |
| M5 Max, 27B 4-bit | batching de saída estruturada | 138 → 210 tok/s |

## llama.cpp b11740 a b11827

Saíram cerca de 60 builds, do b11740 ao b11827 (22/10). A estável continua a v0.7.0. Os builds que importam para o rig (**terceiro**):

- **b11822** (22/10): corrige as entradas de camada do qwen4exp para drafters DFlash ([PR #30927](https://github.com/ggml-org/llama.cpp/pull/30927)).
- **b11808**: o DFlash carrega uma escala opcional da entrada FC (PR #30945).
- **b11755** (20/10): kernel MoE do Metal para 9 experts por token (PR #30699).
- **b11785** (21/10): escala o down-proj MoE por token de expert (PR #30861), testado num M2 Ultra.
- **b11791**: vazamentos de memória do Metal no caminho de captura (PR #30890).
- **b11800**: op fundida para a máscara QSA (PR #30640).
- **b11776**: logprobs com speculative decoding (PR #27196).

As issues #30726 (prefill travado a 262144 no Metal) e #30368 seguem abertas. A PR #30680 (fusão `hc_post` no Metal) não teve atividade. A issue nova #30973 relata o Metal abortando em BF16 MUL_MAT num M4 base. A PR #30982 corrige e está aberta.

## MLX, mlx-lm, MTPLX, LM Studio e Ollama

- **MLX**: continua 0.32.4. A `main` (0.32.5) recebeu kernels quantizados novos (PRs #4682, #4709, #4712) e correções de SDPA para M1/M2.
- **mlx-lm**: continua 0.32.2. A PR #1788 (`qwen4_exp`) não teve atividade desde 04/10.
- **MTPLX**: continua 2.12.2, sem commits. Um contribuidor abriu a PR #650 com o fix da #635. A issue nova #649 relata que o reuso de prefixo entre requests nunca serve no Flash-Next, a 48K e a 185K.
- **LM Studio**: continua 0.4.26, sem beta. A issue #2407 sobre Flash-Next segue aberta.
- **Ollama**: a **0.40.7** final saiu em 18/10, antes da janela. A **0.40.8** (21/10) adiciona o modelo Flint. A **0.40.9-rc2** (22/10) leva o llama.cpp embutido de b11738 para b11803, sem o fix #30927. O Flash-Next continua fora da biblioteca (issue #18071).

## Modelos e packs

A Qwen não publicou nada novo: Flash-Next em `de4b8e4`, 27B em `1d4bf0f`, Qwen3-Coder-Next em `a7fbcb5` (**fabricante**). Não há Qwen4 com pesos.

Os packs da campanha:

- **Swift 1.5** `13839b7`, **iQ-MLX-4.7bpw** `a0e89db`, **Jundot oQ4e-mtp** `c4ddfb5` e **umixer** `73d2cd0`: sem mudança.
- **ggml-org GGUF** foi para **`91fb003`** (21/10). Entraram os sidecars DFlash2 `dflash-Qwen3.8-Flash-Next-{BF16,Q8_0,Q4_0}.gguf` (1.22, 0.65 e 0.35 GB), tirados de `incoai/Qwen3.8-Flash-Next-DFlash2`. Os primeiros shards de IQ4_NL, Q2_K e Q8_0 mudaram em cerca de 64 bytes, e os sidecars MTP em 32 bytes. Os shards de experts não mudaram. O README agora documenta a receita das quants. Não há KLD, PPL nem velocidade publicados ([HF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF)).

Packs novos que cabem em 128 GB (**terceiro**, sem número de M4 Max):

- [`twyx/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-6.6bpw`](https://huggingface.co/twyx/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-6.6bpw) (22/10, `884894d`). Segue a convenção iQ-MLX do ddalcu. Ocupa ~106 GB residentes e ~138 GB de download. A tabela n-gram de 32 GB fica em mmap. A mediana de KLD contra o bf16, em 5 runs, é 0.0023 para o 6.6bpw e 0.0041 para o 4.7bpw. A concordância top-1 é 92.76% contra 91.92%. Não informa velocidade. Sobra pouca memória para KV.
- [`mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX`](https://huggingface.co/mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX) (22/10, `50fa68c`). Converte para MLX/oMLX o modelo coder podado da ISTA-DASLab, de 512 para 256 experts, com uma cabeça MTP Lightning enxertada. Ocupa ~43 GB residentes, mais 38 GB de tabela n-gram no SSD. Mede 94.9 tok/s numa tarefa de código (58.5 sem MTP) e 61.6 tok/s numa tool call, num **M5 Max 128 GB** com oMLX 0.7.2.
- `inferencerlabs/Qwen3.8-Flash-Next-MLX-Q9s` precisa de ~135 GiB e não cabe.

## Comunidade e harnesses

Nenhum relato da janela traz Flash-Next ou 27B medido num M4 Max.

- **OpenCode 1.19.4** (22/10): só atualiza o Bun embutido para 1.4.4.
- **Hermes Agent 0.22.3 e 0.22.4** (21/10): a 0.22.3 junta ~620 PRs, com progresso de MCP em streaming, hook `post_compaction` e seletor de modelo para subagentes. A 0.22.4 traz correções pequenas.
- **Cline**: continua 4.1.25.
- **Crush**: continua v0.98.1, mais uma nightly de 22/10.

## Testes sugeridos

O usuário escolheu os testes 1, 4, 5 e 6. Eles estão em [`bench/stack-updates-2026-10/plan.md`](../bench/stack-updates-2026-10/plan.md).

1. Probe de tool calls e `T_turno` do Swift 1.5 no mlx-serve 26.10.3 contra a 26.10.1.
2. oMLX 0.7.2 nos braços `FR`/`FM`, com MTP de profundidade 1 contra adaptativo, a 256K. Não escolhido.
3. llama.cpp b11822+ com o draft DFlash2 Q8_0 contra draft-mtp. Não escolhido.
4. KLD e decode do twyx iQ-MLX-6.6bpw contra o 4.7bpw no mlx-serve 26.10.3.
5. Splash 1.4.0 com o GGUF do Flash-Next, com `--verify-rows all` e com `auto`.
6. GSQ-RCO-Coder-MLX no oMLX 0.7.2, com decode e uma suíte de código curta.

## Fontes

Linha de base: [`rig-stack-updates-20261019.md`](rig-stack-updates-20261019.md).

- https://github.com/ddalcu/mlx-serve/releases/tag/v26.10.3, /issues/912, /issues/928, /pull/935, /pull/936
- https://github.com/jundot/omlx/releases/tag/v0.7.1, /releases/tag/v0.7.2, /issues/4561
- https://github.com/incoai/splash/releases/tag/1.4.0, /issues/483, /issues/471
- https://github.com/ggml-org/llama.cpp/pull/30795, /pull/30927, /pull/30699, /pull/30861, /issues/30726, /issues/30973
- https://github.com/ml-explore/mlx/releases/tag/v0.32.4, https://github.com/ml-explore/mlx-lm/pull/1788
- https://github.com/youssofal/MTPLX/pull/650, /issues/649
- https://lmstudio.ai/changelog/lmstudio
- https://github.com/ollama/ollama/releases/tag/v0.40.8
- https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF
- https://huggingface.co/twyx/Qwen3.8-Flash-Next-MLX-Serve-iQ-MLX-6.6bpw
- https://huggingface.co/mbrown-uno/Qwen3.8-Flash-Next-GSQ-RCO-Coder-MLX
- https://github.com/anomalyco/opencode/releases/tag/v1.19.4
- https://github.com/NousResearch/hermes-agent/releases
