# Stacks do rig: o que mudou entre 22/10 e 03/11/2026

Três runtimes têm release nova que o rig ainda não instalou: **mlx-serve 26.11.1** (01/11), **oMLX 0.7.3** (31/10) e **llama.cpp v0.8.0** (28/10, primeira estável desde a v0.7.0). O Splash 1.4.1 e o 1.5.0 saíram na janela, e o rig já roda o 1.5.0. A Qwen não mudou nenhum peso. O Qwen4 pode sair nos próximos dias, mas não tem pesos nem data oficial. O Claude Code do rig (2.1.292) está 25 versões atrás, e cinco dessas versões mudam o comportamento contra um `ANTHROPIC_BASE_URL` local.

**Procedência.** A nota junta buscas de 03/11 pela API do GitHub, pela API do Hugging Face, pelo PyPI, pelo changelog do LM Studio, pelo Reddit e pela busca na web. A linha de base é [`rig-stack-updates-20261022.md`](rig-stack-updates-20261022.md), mais o que as campanhas de 23/10 a 02/11 instalaram. As versões instaladas no rig vêm de `ls ~/.local/opt/qwen38/` por SSH em 03/11. As marcas seguem as notas anteriores: **fabricante** é a Qwen, **terceiro** cobre release, issue, PR, card no HF e Reddit, e **medido-no-rig** vem das campanhas deste repo. Nenhum teste rodou para esta nota. Nenhuma fonte da janela traz número de Flash-Next medido num M4 Max. A nota não leu o card de cada pack novo do HF. As seções [Adendo de 04/11](#adendo-de-0411), [Adendo de 05/11](#adendo-de-0511) e [Adendo de 06/11](#adendo-de-0611) registram o que saiu nos três dias seguintes.

## Resumo por stack

| Stack | No rig em 03/11 | Último em 03/11 | Impacto no rig |
|---|---|---|---|
| mlx-serve | 26.10.3 (driver diário) | **26.11.1** (01/11) | Correções de tool call e de MTP; variáveis `MLX_SERVE_*` antigas removidas (teste 1) |
| oMLX | 0.7.2 | **0.7.3** (31/10) | Flash-Next oQ4e +24% de decode no M3 Ultra; KV de batch sem cópia (teste 2) |
| Splash | 1.5.0 | 1.5.0; `main` com fix de tool call | 1.4.1 carrega GGUF com experts podados; #471 aberta |
| llama.cpp | b11569, b11609 | **v0.8.0** estável (28/10); build b12069 | Mudanças no QSA do qwen4exp e no DFlash2 (teste 3) |
| MLX core | — | 0.32.4 (sem release) | Nenhum |
| mlx-lm | — | 0.32.2 (sem release); PR #1788 parada | Nenhum |
| MTPLX | 2.12.2 | 2.12.2, sem commits | Continua fora do plano |
| LM Studio | backend mlx-llm 1.11.0 | **0.4.28** (31/10) | Controles de memória e de prefill na Neural Engine para o Splash |
| Ollama | não instalado | **0.40.14** (03/11) | Ainda sem Flash-Next na biblioteca |
| Modelos Qwen | Flash-Next `de4b8e4`, 27B `1d4bf0f` | sem mudança; Qwen4 sem pesos | Nenhum agora |
| Packs da campanha | Swift 1.5 `13839b7`, iQ `a0e89db`, ggml-org `91fb003` | sem mudança | Nenhum |
| Claude Code | 2.1.292 (rig), 2.1.302 (MacBook) | **2.1.317** (03/11) | Timeout de stream, tool search e compactação mudam contra servidor local (teste 4) |
| Outros harnesses | OpenCode 1.18.31, Hermes 0.21.2 (MacBook) | OpenCode **1.19.5** e **2.2.5**, Hermes **0.22.6**, Crush **0.99.0**, Cline **4.1.26**, Codex **0.166.0** | Nenhum direto |
| macOS | 26.6.2 | 26.7.2 (só segurança) | Nenhum |

## mlx-serve 26.11.1

A **v26.11.1** saiu em 01/11 (**terceiro**, [release](https://github.com/ddalcu/mlx-serve/releases/tag/v26.11.1)). A maior parte das notas trata de DeepSeek-V4.1-Flash, plugins, mídia e app. As mudanças que tocam o driver diário:

- "Other's Flash-Next packs load": packs de Flash-Next de outros autores passam a carregar. As notas não dizem quais.
- Um thinking budget não desliga mais o speculative decoding da resposta.
- Marcadores de tool call soltos não aparecem mais como resposta. Texto com forma de token especial é lido como texto.
- O prompt cache fica mais estável em servidores que rodam por muito tempo.
- O último chunk de um stream traz os timings, na API OpenAI e na Anthropic.
- Um schema que o servidor não consegue impor é recusado na entrada.
- **Muitas variáveis `MLX_SERVE_*` de tuning foram removidas**, porque o que elas ligavam virou padrão. Os launchers do rig usam só `MLX_SERVE_EXPECTED_VERSION`, que é do repo, mas a release não lista as variáveis removidas. Conferir o `--help` e o log de boot antes de trocar.

Estado das issues acompanhadas:

- A PR **#935** (DFlash2 no Flash-Next) fechou em 29/10 **sem merge**. A última revisão do bot do mantenedor, em 22/10, apontou uma regressão no caminho MTP padrão do Flash-Next.
- A **#844** (prefix cache só em disco) e a **#853** (DFlash2 mais lento a 128K no 27B) seguem abertas.
- Depois da release, a `main` recebeu "perf: fast gguf qwen" (02/11) e kernels IQ mais rápidos no caminho GGUF (03/11).

## oMLX 0.7.3

A **v0.7.3** saiu em 31/10, depois da 0.7.3.dev1, dev2 e rc1 (**terceiro**, [release](https://github.com/jundot/omlx/releases/tag/v0.7.3)). As mudanças para o Flash-Next e para agentes:

| Mudança | Resultado publicado | Chip |
|---|---|---|
| Decode do Flash-Next mais rápido (rc1) | Flash-Next oQ4e: 65.6 → 81.5 tok/s (+24%); 4 requests 167.6 → 186.5 tok/s | M3 Ultra |
| KV de batch atualizado no lugar (#4916, #4936, #4954, #4971) | 8 streams MTP a 81K: pico 248.0 → 161.1 GiB, decode 180.7 → 241.1 tok/s | M3 Ultra |
| Batch lê cada peso uma vez para todas as linhas (#4977, #4990) | 8 conversas de agente a partir de 160K: saída 36.4 → 42.4 tok/s | M3 Ultra |
| Qwen híbridos reusam um system prompt compartilhado entre conversas (#4994) | 5 requests com 6.5K de system prompt: TTFT 0.89 → 0.25 s (Qwen3.5-0.8B) | M3 Ultra |
| Backoff do MTP de batch entre requests (dev2, #4810) | 8 clientes no Flash-Next: +3% no M3 Ultra, +11% no M5 Max | — |

Outras mudanças:

- `/v1/chat/completions` devolve `logprobs` e `top_logprobs`, também com MTP Lightning ligado (#4859).
- `ignore_eos` em `/v1/chat/completions` e `/v1/completions` (#4978).
- O oMLX serve GGUFs do Flash-Next com pastas de variante de PLE pelo Splash (#4821) e GGUFs com experts podados (#4870).
- O model manager baixa só os arquivos que mudaram no HF (#4949).

A **#4561** (Prefill Memory Guard recusa requests longos num rig de 128 GB) segue aberta, sem atualização desde 16/10. Nenhum número da release vem de M4 Max no Flash-Next. O único número de M4 Max é do Flint.

## Splash 1.4.1 e 1.5.0

O rig já tem os dois em `~/.local/opt/qwen38/`, e a campanha [`claude-code-concurrency-2026-11`](../bench/claude-code-concurrency-2026-11/) usou o 1.5.0. Esta seção registra o que importa para os próximos testes (**terceiro**, [1.4.1](https://github.com/incoai/splash/releases/tag/1.4.1), [1.5.0](https://github.com/incoai/splash/releases/tag/1.5.0)).

- **1.4.1** (26/10): carrega GGUFs com experts podados, incluindo os GSQ-RCO-Coder da ISTA (#561). A 1.4.0 recusava esses GGUFs (#527), e por isso o Task 5b de [`splash-longctx-2026-10`](../bench/splash-longctx-2026-10/plan.md) ficou condicional. A 1.4.1 também corrige requests na fila que travavam sob pressão de memória (#579) e aceita GGUF dividido cujo primeiro arquivo só tem metadados (#560).
- **1.5.0** (28/10): `--model-dir` serve um GGUF ou uma pasta MLX local sem o Hub, e `--draft-model` aponta um draft DFlash2 local. Kernels quantizados mais rápidos no M3, M4 e M5 (#600, #602), sem número de modelo inteiro no M4. A soma dos kernels mudou, então a saída greedy pode mudar um pouco. Abreviações de opções da CLI, como `--max-mem`, não são mais aceitas. Os caches persistentes de MoE começam frios uma vez.
- **`main` depois da 1.5.0**: uma tool call sem nome de função passa a ser lida como texto (#632). O expert store devolve e retoma memória (#645). O instalador sugere o Flash-Next IQ3_S em Macs com 96 GB ou mais (#643). Nenhuma release contém isso ainda.
- A **#471** (Swift 1.5 MLX não carrega) segue aberta.

## llama.cpp v0.8.0 e builds até b12069

A **v0.8.0** saiu em 28/10 (**terceiro**, [release](https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0)). É a primeira estável depois da v0.7.0 e leva o ggml para a v0.28.0. O rig tem só os builds b11569 e b11609. As mudanças que importam:

- **b11822** (#30927): entradas de camada do qwen4exp para drafters DFlash. Já estava na nota de 22/10.
- **b11886** (25/10): qwen4exp sem `cont` e sem pré-escala.
- **b11936** (#30965, 27/10): o qwen4exp monta a seleção QSA sem a `kq_mask`, sobre a op fundida `GGML_OP_TOP_K_MASK` (#31230, Metal no b11927).
- **#30663**: amostragem probabilística para drafts DFlash2.
- **b11866** (#30924): o Metal tira o reescalonamento amax do `mul_mm_id`.
- **b11895** (#30072): o Metal corrige overflow em offsets grandes de saída de matriz.
- **b11985** (#31075): mat-vec MXFP4 mais rápido no Metal.
- **b12063** (#31506, 03/11): o DFlash copia hidden features por cópia no device.

A **#30726** (prefill travado a contexto grande no Metal com qwen4exp) e a PR **#30680** (fusão `hc_post` no Metal) seguem abertas, sem atividade desde 17/10 e 16/10. A PR **#30982** (`mul_mm` para 32 ≤ K < 64 no Metal) segue aberta.

## MLX, mlx-lm, MTPLX, LM Studio e Ollama

- **MLX**: continua 0.32.4 (14/10). **mlx-lm**: continua 0.32.2 (16/10). A PR #1788 (`qwen4_exp`) não teve atividade desde 04/10. O **mlx-vlm** foi para 0.7.11 (28/10).
- **MTPLX**: continua 2.12.2, sem commits desde 22/10. A PR #650 e as issues #635 e #649 seguem abertas.
- **LM Studio**: **0.4.27** (29/10) traz controles de memória máxima e de prefill na Neural Engine para modelos do Splash, e corrige o draft que ficava selecionado ao trocar para MTP embutido. **0.4.28** (31/10) corrige o template do Flint. O changelog não cita Flash-Next nem DFlash na janela. A issue #2407 (Flash-Next no LM Studio) segue aberta. O **Bionic 1.1.10** (29/10), o app de agentes da mesma empresa, ganhou um motor oMLX.
- **Ollama**: 0.40.9 a **0.40.14**. A 0.40.14 (03/11) faz os endpoints OpenAI usarem os defaults de sampling do modelo quando o cliente não manda `temperature`/`top_p`, e faz o `ollama launch claude` aplicar o limite de saída do modelo. O Flash-Next continua fora da biblioteca (issue #18071).

## Modelos e packs

A Qwen não publicou pesos novos: Flash-Next em `de4b8e4`, 27B em `1d4bf0f`, Qwen3-Coder-Next em `a7fbcb5` (**fabricante**). O Qwen4 não tem repo no HF.

- No Apsara de 29/10, o CTO da Alibaba Cloud disse que o Qwen4 pode sair "na semana". Relatos de terceiros citam Qwen4-Max, -Flash, -Plus e um 27B de pesos abertos, e um PR do qwen-code cita contexto de 1M. Nada disso é anúncio oficial com data ([Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1xif6lf/apsara_conference_qwen4_next_week/), [Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1xi7390/qwen4_1m_context_window/), [cellcog](https://cellcog.ai/blog/qwen-4-release-date/)).
- Em 02/11, a Qwen declarou que os modelos continuam open source ([Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1xm28e6/official_statement_qwen_models_will_stick_to_open/)).

Os packs da campanha não mudaram: Swift 1.5 `13839b7`, iQ-MLX-4.7bpw `a0e89db`, ggml-org GGUF `91fb003`, Swift 1.5 GGUF `0142554`, DFlash2 `a22a174`, twyx 6.6bpw `884894d`, GSQ-RCO-Coder-MLX `50fa68c`.

Packs novos: os 40 repos de Flash-Next mais novos do HF são quase todos abliterated, uncensored ou formatos de NVIDIA (NVFP4, exl3, FP8). O mais baixado da janela, `autotrust/Qwen3.8-Flash-Next-E384-FP4-*`, é FP4 para NVIDIA. O `taurusduan/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF` (02/11) é cópia do `ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF`, que existe desde 24/09 (IQ3_S 83.7 GB, IQ3_XXS 76.0 GB, IQ2_XS 68.2 GB). Nenhum desses packs publica velocidade num Mac.

## Harnesses

**Claude Code 2.1.292 → 2.1.317** (**terceiro**, [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)). Cinco versões mudam o comportamento contra um `ANTHROPIC_BASE_URL` local, como o mlx-serve e o Splash do rig:

- **2.1.299**: um stream sem dados por um `ANTHROPIC_BASE_URL` custom só aborta depois de 300 s, não mais 180 s. O cold TTFT do Flash-Next a 256K no rig é ~350 s ([splash-speed-tradeoffs](splash-speed-tradeoffs-20261024.md)), então um prefill frio a 256K ainda passa do limite. Na mesma versão, uma sessão com nome de modelo de gateway não para mais com "Prompt is too long" perto de 200K.
- **2.1.304**: tool search fica ligado por padrão atrás de um `ANTHROPIC_BASE_URL` custom. Um 400 ou 422 do servidor faz o Claude Code repetir o request sem tool search. **2.1.314**: um servidor que recusa blocos `tool_reference` recebe o request de novo sem tool search, e a sessão lembra.
- **2.1.307**: o header beta `prompt-caching-scope` não é mais enviado atrás de um `ANTHROPIC_BASE_URL` custom.
- **2.1.316**: `CLAUDE_CODE_SUBAGENT_EFFORT` define o effort dos subagentes. `/model <id>` avisa quando o modelo é desconhecido e o auto-compact vai assumir 200K de janela.

Esses itens mudam a forma dos requests que a campanha de concorrência mediu com a 2.1.292. Um rerun com a 2.1.317 não é comparável sem registrar a versão.

Outros harnesses:

- **OpenCode**: a linha 1.x foi para **1.19.5** (28/10, um fix de TUI), e a linha 2 chegou a **2.2.5** (30/10). A 2.2.0 (27/10) traz TTL de prompt cache configurável por provider e modelo, e instruções de sessão por plugin que não invalidam o prompt cache. O MacBook roda 1.18.31.
- **Hermes Agent**: 0.22.5 (22/10) e **0.22.6** (02/11, ~776 PRs). O MacBook roda 0.21.2.
- **Crush**: **v0.99.0** (29/10), com Catwalk v3 e hooks em toda a execução.
- **Cline**: **4.1.26** (26/10), focada em tarefas na nuvem. **Codex CLI**: **0.166.0** (29/10).

## macOS

O rig roda macOS 26.6.2. A última versão é a 26.7.2, que só traz correções de segurança e não cita Metal ([ithinkdiff](https://www.ithinkdiff.com/macos-tahoe-26-7-2-macos-sequoia-15-8-2-security-updates/)). O app do Splash 1.5.0 pede macOS 26.4 ou superior e M3 ou superior, e o rig atende os dois. [`docs/machine-configuration.md`](../docs/machine-configuration.md) ainda diz 26.3.

## Adendo de 04/11

Buscas de 04/11 pela API do GitHub, pela API do Hugging Face, pelo PyPI e pelo r/LocalLLaMA. Nenhum teste rodou. Todos os números abaixo são **terceiro**, e nenhum vem de M4 Max no Flash-Next, exceto onde a linha diz.

| Stack | Novo em 04/11 | Impacto no rig |
|---|---|---|
| mlx-serve | sem release; `main` com #1075, #1081 e MLX 0.32.5 pré-release | Checkpoint de fim de decode no `qwen4_exp` corrigido (teste 6) |
| oMLX | **0.7.4.dev1** (dev) | Prefill sob pressão de memória em 128 GB; ordem de tool results paralelos |
| llama.cpp | **v0.9.0** estável; build b12114 | Estado de conv do qwen4exp e hidden state do MTP nos checkpoints |
| Pack Unsloth do Flash-Next | **Dynamic V3.1** (17:43 UTC) | UD-IQ4_XS refeito: números antigos não valem para o arquivo novo (teste 7) |
| Claude Code | **2.1.318** | Nada novo contra `ANTHROPIC_BASE_URL` local |
| Outros | Hermes **0.22.7**, Ollama **0.40.15-rc0**, Codex 0.168 só alphas | Nenhum direto |

Sem mudança em 04/11: Splash, MLX e mlx-lm no PyPI (0.32.4 e 0.32.2), MTPLX, OpenCode, Cline e os pesos da Qwen no HF.

**mlx-serve, `main`.** Nenhum dos três itens está numa release.

- **#1075** (bug sweep): no `qwen4_exp`, um stop serial pulava o checkpoint de fim de decode (#1004). O turno seguinte restaurava em prompt−31 e refazia o prefill da resposta. Agora restaura em prompt+resposta+2 em 3 de 3 probes. O autor rodou o probe e as trocas de modelo num M4 Max 128 GB. A mesma PR faz uma carga recusada por memória descarregar modelos ociosos e tentar de novo, e corrige o histórico de agente que mandava tool call sem resultado após truncar.
- **#1081**: cada conversa de plugin guarda até 3 checkpoints abaixo do último (`MODULE_RUNGS_KEPT`). Um request que ramifica abaixo do último checkpoint (recap, título, compactação, regenerate) passa a usar o cache. Medido em DeepSeek V4.1 num Studio de 256 GB: tokens em cache no fork 0 → 28,596, TTFT 8.72 → 0.13 s. O custo é ~1 MB de memória por 1K tokens de checkpoint em DeepSeek V4.1. A PR não mede o Flash-Next.
- A `main` passou para um pré-release do MLX 0.32.5 e refez as provas de Metal no M5.

**oMLX 0.7.4.dev1** ([release](https://github.com/jundot/omlx/releases/tag/v0.7.4.dev1)). É release de desenvolvimento.

| Mudança | Resultado publicado | Chip |
|---|---|---|
| Chunks largos de prefill sob pressão de memória em Macs de 128 GB (#4902) | Flash-Next oQ4e, prompts de 34.5K em sequência: prompt mais lento 90.7 → 13.1 s | M5 Max 128GB |
| Checkpoints FP16 do Flash-Next com os kernels fundidos de hyper-connection e GDN (#5028) | oQ2.5e fp16, MTP off, 32K: decode 38.9 → 63.0 tok/s | M3 Ultra |
| Decode após prompt longo (#4901) | +3 a 5% | M5 Max |
| Batch de 6 linhas em camadas 8-bit lê cada peso uma vez | Qwen3.8-27B oQ8e, 6 requests: 62.2 → 72.4 tok/s | M5 Max |

- **#5012**: os resultados de tool calls paralelas chegam ao chat template na ordem das calls, em `/v1/messages` e `/v1/chat/completions`. Antes, o Qwen podia ligar um resultado à call errada.
- `/v1/messages` passa a continuar uma mensagem final de assistant como prefill (#4995). Isso muda o comportamento para um cliente que manda assistant no fim.
- O Prefill Accelerator (#5065) usa um segundo Mac para o prefill. O rig tem um Mac só.
- A **#4561** segue aberta.

**llama.cpp v0.9.0** ([release](https://github.com/ggml-org/llama.cpp/releases/tag/v0.9.0)). Leva o ggml para a v0.29.0. Itens que tocam o Flash-Next:

- **#31443**: o qwen4exp grava a cauda do estado de conv sem `cont` intermediário.
- **#30141**: o speculative decoding salva e restaura o hidden state do MTP nos checkpoints de contexto. **#31350**: o servidor restaura o checkpoint especulativo para drafts maiores que `n_rs_seq`.
- **#29510**: a op `flash_attn_ext_rows` torna eficiente o KV unificado com várias sequências.
- **#30881**: API de cópia de tensores em lote, com implementação Metal.
- **#30726**, **#30680** e **#30982** seguem abertas.

**Unsloth Dynamic V3.1.** O `unsloth/Qwen3.8-Flash-Next-GGUF` foi atualizado em 04/11 ([card](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF), [Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1xnvbxn/new_qwen38flashnext_unsloth_dynamic_v31_ggufs/)). Segundo o autor no Reddit, os quants de UD-IQ4_XS para baixo usam o método novo. O UD-Q4_K_XL mudou só para o engram switching funcionar, sem mudar os pesos. As campanhas `qwen38-flashnext-daily-driver-2026-09`, `splash-longctx-2026-10` e `stack-updates-2026-10` usaram o `UD-IQ4_XS` desse repo. Os resultados dessas campanhas valem para o arquivo antigo.

**Claude Code 2.1.318** ([release](https://github.com/anthropics/claude-code/releases/tag/v2.1.318)). Corrige sessões no macOS que travavam com muitos comandos Bash rodando. Subagentes em background mandam um comando shell para background depois de 3 min em todos os providers. Nenhum item cita `ANTHROPIC_BASE_URL` custom.

**Outros.** O Hermes **0.22.7** (03/11) junta ~174 PRs, e as notas detalhadas ficam para a 0.23.0. O Ollama **0.40.15-rc0** adiciona o MiMo V2.6. No r/LocalLLaMA, o Kimi-K3.1-Pro virou open-weights em 04/11. A nota não conferiu o tamanho dele contra os 128 GB do rig.

## Adendo de 05/11

Buscas de 05/11 até 16:40 UTC pela API do GitHub, pela API do Hugging Face, pelo PyPI e pelo r/LocalLLaMA. Nenhum teste rodou. Todos os números abaixo são **terceiro**.

| Stack | Novo em 05/11 | Impacto no rig |
|---|---|---|
| mlx-serve | **26.11.2** no CHANGELOG da `main`, sem tag nem release | Primeiro número de Flash-Next iQ-MLX 4.7bpw num M4 Max na tabela do projeto; residência Metal entre requests (teste 8) |
| llama.cpp | builds até b12128; **#30982** com merge | `mul_mm` para 32 ≤ K < 64 no Metal, acompanhada desde 22/10 |
| oMLX | só commits na `main` | Nenhum direto |
| Modelos Qwen | Flash-Next `7ecef55`, 27B `8c0b3d3` | Só o model card mudou (cores da tabela em dark mode); pesos e config iguais |
| Outros | Codex 0.168 só alphas; Crush nightly | Nenhum |

Sem mudança em 05/11: Splash, MLX e mlx-lm no PyPI (0.32.4 e 0.32.2), MTPLX, Claude Code (2.1.318), OpenCode, Hermes, Ollama e Cline.

**mlx-serve 26.11.2** ([CHANGELOG](https://github.com/ddalcu/mlx-serve/blob/main/CHANGELOG.md), [benchmarks.md](https://github.com/ddalcu/mlx-serve/blob/main/benchmarks.md)). O commit `ac064dd` escreve a entrada da versão e as colunas de M5 Ultra e de M4 Max, mas a última release no GitHub ainda é a 26.11.1. A entrada junta a #1075, a #1081 e o MLX 0.32.5. Para o rig:

- A tabela de decode do projeto num **M4 Max 128 GB** ganha a coluna 26.11.2. O **Flash-Next iQ-MLX 4.7bpw** (a mesma família de pack da campanha, de commit não informado) aparece a **83 tok/s com MTP**, sem coluna anterior para comparar. O Qwen3.8-27B iQ-MLX 3.8bpw vai de 62 para 59 tok/s (−5%). A tabela usa o `llmprobe` e não diz o tamanho do prompt.
- O Flash-Next passa a reusar a resposta em cache no turno seguinte de agente (#1075, já no adendo de 04/11).
- Plugins externos compilados para a 26.11.1 precisam de rebuild.
- **#1094** (com merge em 05/11): o macOS tira a residência Metal ~2 s depois que a GPU fica ociosa, e o MLX só pede residência uma vez por conjunto. Entre requests, um modelo perto do tamanho da RAM é comprimido, e o Mac pode entrar em panic (#1090). O mlx-serve agora exporta `MLX_METAL_RESIDENCY_REFRESH_INTERVAL_MS=1000` no macOS, a menos que o usuário defina a variável. Medido num M4 Max com o Qwen3.8-27B iQ 3.8bpw, memória wired depois de um request:

| | t+0 | t+5 s | t+20 s |
|---|---:|---:|---:|
| refresh desligado (padrão antigo) | 18.8 GB | 5.2 GB | 5.1 GB |
| #1094 | 18.8 GB | 18.5 GB | 18.2 GB |

O Flash-Next do driver diário ocupa a maior parte dos 128 GB, então ele é o caso que a #1090 descreve. O [Adendo de 06/11](#adendo-de-0611) mostra que o MLX da 26.10.3 não lê essa variável.

- A **#844** (prefix cache só em disco) fechou em 04/11 como resolvida. Segundo o mantenedor, o warm turn não teria mais margem que o cold turn, então adiar para o SSD não mudaria a admissão.
- A **#853** segue aberta.

**llama.cpp, builds b12115 a b12128.** Não saiu estável nova. Itens que tocam o Metal ou o Flash-Next:

- **#30982** (merge em 05/11): o Metal usa `mul_mm` para 32 ≤ K < 64.
- **#31688**: o Metal mantém grupos de nós fusíveis dentro de um command buffer.
- **#31660**: os snapshots de conv do MTP de todo modelo recorrente vão num único `set_rows`.
- **#30137**: o `llama-server` usa checkpoints com contagem de referência em vez de cópias profundas.
- **#30541**: corrige o tamanho da cópia de estado no device para KV quantizado.
- A **#30726** e a **#30680** seguem abertas, sem atividade desde 17/10 e 16/10.

**oMLX, `main`.** A #4866 mantém janelas largas de verificação MTP no kernel fundido do TurboQuant. A #5082 desliga o cache SSD do Splash quando o cache do oMLX está desligado. Nenhuma release nova. A **#4561** segue aberta.

**Packs.** No HF, os 12 repos de Flash-Next mais novos de 05/11 são quase todos uncensored, abliterated ou NVFP4. Um deles, `austindixson/Qwen3.8-Flash-Next-Unsloth-V3.1-MLX`, converte o pack V3.1 para MLX, e a nota não leu o card. No r/LocalLLaMA, um guia com RTX 5080 mede a perplexidade do novo Unsloth `UD-IQ3_XXS` em wikitext: 3.247, contra 3.382 do GSQ-RCO IQ3_S e 3.273 do BF16, com 1 a 3,5% menos decode ([Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1xomy0i/guide_qwen38_flashnext_on_a_single_rtx_5080_64gb/)). O número é de uma pessoa, em NVIDIA.

## Adendo de 06/11

Buscas de 06/11 até 20:00 UTC pela API do GitHub, pela API do Hugging Face, pelo PyPI e pelo r/LocalLLaMA. Nenhum teste rodou. O `mac-studio` não respondeu por SSH nesta sessão, então as versões instaladas no rig continuam as de 03/11. Todos os números abaixo são **terceiro**.

| Stack | Novo em 06/11 | Impacto no rig |
|---|---|---|
| mlx-serve | release **v26.11.2** | Palavra de effort deixa de cortar o thinking (teste 10); só esta release lê a variável de residência (teste 8) |
| Splash | **1.6.0** | Correção ligada à queda de decode da #644 num Mac de 128 GB com Flash-Next (teste 9); mudanças de API e de GGUF |
| llama.cpp | builds até b12177; **#31233** com merge | Cache de experts mais eficiente, sem número em Metal; o repo não usa esse cache |
| Claude Code | **2.1.319** | Muda o auto mode atrás de gateway; nenhum script do repo usa auto mode |
| Hermes | **0.23.0** | Um gateway por máquina e endpoints custom mais estáveis; o MacBook roda a 0.21.2 |
| Modelos | Ripple-65B Preview; suporte a Xing 4.0 no llama.cpp | Nenhum direto |
| Outros | Crush **0.100.0** (subagentes); Codex **0.167.0** | Nenhum direto |

Sem mudança em 06/11: release do oMLX, MLX e mlx-lm no PyPI (0.32.4 e 0.32.2), MTPLX, Ollama, Cline e os pesos da Qwen (os SHAs seguem iguais aos de 05/11). O OpenCode só publicou o `process-daemon-v0.5.0`.

**mlx-serve v26.11.2** ([release](https://github.com/ddalcu/mlx-serve/releases/tag/v26.11.2)). A release saiu às 02:15 UTC e inclui a #1075, a #1081, a #1094 e o MLX 0.32.5. Dois pontos mudam o plano do rig:

- **Thinking sem corte por palavra.** O commit `0bfdff0` remove os cortes de 1024, 2048 e 8192 tokens de `minimal`, `low` e `medium`. Ele remove também o corte implícito de 2048 tokens em um request de Qwen3.8 sem effort, que valia quando os marcadores de thinking são tokens atômicos. Agora só `--reasoning-budget`, o budget do request ou uma regra do modelo limitam o thinking. A mudança vale para chat, messages e responses, então ela alcança o `output_config.effort` do Claude Code. O CHANGELOG põe o corte implícito na v26.9.5, e o código da 26.11.1 ainda o tem. A nota não leu o código da 26.10.3. Depois do upgrade, o `T_turno` e os tokens de raciocínio não comparam com os números antigos, a menos que o teste fixe `--reasoning-budget`. No `agent_probes.py`, o padrão `xhigh` já não tinha corte, mas o `effortswitch` troca para `medium` por padrão.
- **Correção do adendo de 05/11: a variável de residência não funciona na 26.10.3.** O MLX cria `MLX_METAL_RESIDENCY_REFRESH_INTERVAL_MS` no commit `a59cc23`. A 26.10.3 e a 26.11.1 fixam `lib/mlx-src` em `64ea011` (MLX 0.32.3), 53 commits antes dele. A 26.11.2 fixa `c69303b`, que contém o commit. Portanto, o driver diário só ganha a correção com o upgrade.

Outros itens da release: um fork de chat longo de Flash-Next no SSD retoma de um checkpoint em 5 s, contra 46 s. Uma resposta que repete o mesmo parágrafo com outro final é cortada. O Flash-Next deixa de quebrar quando um request de imagem divide a GPU com outros chats. O `--mlx-gguf` aceita mais famílias GGUF, entre elas Qwen3, e a nota não conferiu se o Flash-Next entra nessa lista.

**Splash 1.6.0** ([release](https://github.com/incoai/splash/releases/tag/1.6.0), [notas](https://github.com/incoai/splash/blob/1.6.0/docs/release-notes/1.6.0.md)). A release muda pouco os kernels e muda a memória, o scheduler e a recuperação do engine. O decode de um request fica a até 2% da 1.5.0. Para o rig:

- **#644** descreve o Splash 1.5.0 num Mac de 128 GB com `Qwen3.8-Flash-Next-GSQ-RCO-GGUF:Q2_0`, limite de 96 GiB, contexto de 262144 e 1 a 3 streams. A mediana de decode cai de 58.5 tok/s para 26.0 tok/s em 3 h, e um prompt de 64 tokens com a máquina ociosa mede 11.8 tok/s. O pool de KV fica 99.7% ocupado por prefixos antigos. Esse perfil é próximo ao das campanhas longas do rig no Splash 1.5.0, e a nota não reanalisou essas campanhas.
- A 1.6.0 tira o KV em cache do residency set da fila da GPU. O resumo da release diz que o KV ocioso não atrasa mais cada comando. As notas detalhadas dizem que a equipe não reproduziu a queda e que a mudança não prova o fim dela. As notas não citam o `--kv-high-water` que usuários testaram na #644. O teste 9 cobre esse ponto.
- Números da release, num M5 Max de 36 GB com `--max-memory 18G`: a maior pausa de stream cai de 300–406 s para 0.92 s, com 1.27x de prefill e 1.25x de decode em carga concorrente.
- **Segurança:** com `http_proxy` definido, o launcher da 1.5.0 enviava a API key do servidor ao proxy. A 1.6.0 corrige isso. Trocar a chave se o rig usou esse caso.
- **Thinking:** o corte de um budget agora segue o chat template, e o turno seguinte reusa mais KV em cache. O budget também encolhe quando resta pouco contexto.
- **Mudanças que podem quebrar:** o `/status` vai ao schema 8 e remove `kv_spill.history_stream.contended_commands` e `memory_plan.budget.resident_kv_bytes`. Nenhum script `.py` ou `.sh` do repo lê esses campos. Um request encerrado por stop sequence passa a contar como `completed`. O `stop_sequences` de Messages precisa ser array. Um GGUF com tensores que o modelo não usa é recusado na carga, então o teste 9 confere primeiro se o pack do rig carrega. O cache persistente de um GGUF recomeça uma vez, então a primeira execução não entra em benchmark.
- GGUFs de Flash-Next com tabela PLE em BF16 ou F16 agora carregam. O app sugere o IQ3_S em Macs com 96 GB ou mais (#643).

**llama.cpp, builds até b12177.** Não saiu estável nova. A **#31233** (merge em 06/11) troca o SLRU do `moe-cache` por oito classes com pontuação de uso. O PR mede +6% de decode no Flash-Next UD-Q4_K_XL com cache quente de 15 GB e 8% menos uploads. O texto do PR não cita Metal, e o repo não usa `moe-cache`. Nenhum título de commit cita Metal ou MTP desde 05/11 12:00 UTC. A #30726 e a #30680 seguem abertas.

**oMLX.** Sem release e sem commit novo desde 05/11 16:00 UTC. A **#4561** segue aberta. Um comentário de 06/11 não reproduz a recusa num M2 Max com um prompt de ~120.000 caracteres, e o autor diz que precisa de um prompt maior ou de um hot cache maior. Os testes unitários seguem como evidência da correção.

**Harnesses.** O Claude Code **2.1.319** muda o auto mode com telemetria ou feature flags desligadas, inclusive atrás de LLM gateways: uma chamada que o servidor não confere é perguntada ou negada, sem o classificador local. `CLAUDE_CODE_AUTO_MODE_SERVER=0` mantém o comportamento antigo. A nota não testou se um `ANTHROPIC_BASE_URL` local conta como gateway. O Hermes **0.23.0** põe um gateway por máquina como dono de cada sessão, estabiliza os endpoints `custom:` e corrige tool calls divididas no streaming do LM Studio. Ele remove as ferramentas `browser_*`, e nenhum script do repo as cita. O runtime local embutido do Hermes usa o llama.cpp b11671.

**Modelos.** O Qwen4 segue sem pesos: o modelo mais novo na listagem da Qwen no HF é o Qwen-Image-2.1-Turbo, de 09/10. Um post no r/LocalLLaMA fala de preview no site da Qwen, e a nota não conferiu isso. O **Ripple-65B Preview** (04/11, Apache 2.0) é um modelo denso com contexto de até 1 Mi. O card marca 80.52 no TerminalBench 2.1 e diz que o modelo foi feito para hardware NVIDIA. Uma tabela no Reddit, montada a partir dos cards, põe o Flash-Next à frente no DeepSWE 1.1 (58.7 contra 44.3) e o Ripple à frente no SWE Bench Pro (79.1 contra 62.5), com versões que podem diferir. O llama.cpp ganhou suporte ao Ripple (#31692) e ao Xing 4.0 (#31589). Há conversões MLX do Ripple no HF, e a nota não leu esses cards.

## Testes sugeridos

1. **mlx-serve 26.11.2 contra a 26.10.3** no Swift 1.5 (`w1z`): probe de tool calls com `frequency_penalty` 0 e `T_turno` a 32K e 128K. Conferir antes se o boot avisa sobre variáveis removidas.
2. **oMLX 0.7.3 contra a 0.7.2** nos braços `FR`/`FM`: `T_turno` com 1 stream e com 2 streams. O ganho publicado é de M3 Ultra e de batch, e a campanha de concorrência é onde ele apareceria.
3. **llama.cpp v0.8.0** com o GGUF do Flash-Next e o draft DFlash2 Q8_0, contra draft-mtp. É o teste 3 da nota de 22/10, que não rodou, agora numa estável.
4. **Claude Code 2.1.317 contra a 2.1.292** numa tarefa da `claude-code-concurrency-2026-11` no Splash 1.5.0: contar os requests com tool search e os retries 400/422 no proxy `request_log.py`.
5. **Task 5b da `splash-longctx-2026-10`**: o GSQ-RCO-Coder GGUF no Splash 1.4.1 ou posterior, se a campanha ainda não cobriu esse braço.
6. **mlx-serve 26.11.2** contra a 26.10.3 no Flash-Next: contar os tokens em cache no turno seguinte a uma resposta encerrada por stop. Pelo PR, o turno deve restaurar em prompt+resposta+2.
7. **Unsloth `UD-IQ4_XS` V3.1 contra o arquivo antigo** no llama.cpp ou no Splash: tamanho, decode e uma tarefa de tool call. Registrar o commit do HF de cada arquivo. **Resultado (10/11):** [`flashnext-weights-2026-11/results/summary.md`](../bench/flashnext-weights-2026-11/results/summary.md). No Splash 1.5.0, o V3.1 (`084c631`) decodifica 11% mais rápido que o arquivo de `766911a`, com a mesma qualidade. Ele gasta mais tokens, não menos, e acerta menos sessões de tool calls com `frequency_penalty` 1. O Swift 1.5 `IQ4_XS` continua o peso do rig.
8. **Residência Metal no driver diário**: medir a memória wired do Flash-Next a t+0, t+5 s e t+20 s depois de um request, em três braços: 26.10.3, 26.11.2 padrão e 26.11.2 com `MLX_METAL_RESIDENCY_REFRESH_INTERVAL_MS=0`. Medir também o TTFT do request seguinte depois de 20 s ocioso. A variável não tem efeito na 26.10.3.
9. **Splash 1.6.0 contra a 1.5.0** com o GSQ-RCO do rig e `--max-memory` de 96 GiB. Conferir antes se o GGUF carrega. Descartar a primeira execução da 1.6.0, porque o cache recomeça. Rodar uma carga de agente de 4 h, com o decode por hora, `pages_cache` no `/status` e um prompt de 64 tokens no fim. **Resultado (08/11):** [`splash16-2026-11/results/summary.md`](../bench/splash16-2026-11/results/summary.md). O launcher fica na 1.5.0, porque duas sessões de 256K ficam até 65% mais lentas na 1.6.0. A queda da #644 não apareceu em nenhuma release.
10. **Thinking na 26.11.2**: rodar o probe de tool calls e uma tarefa de agente sem `--reasoning-budget` e com `--reasoning-budget 2048`. Registrar os tokens de raciocínio, o `T_turno` e a taxa de conclusão.

## Fontes

Linha de base: [`rig-stack-updates-20261022.md`](rig-stack-updates-20261022.md).

- https://github.com/ddalcu/mlx-serve/releases/tag/v26.11.1, /pull/935, /issues/844, /issues/853
- https://github.com/jundot/omlx/releases/tag/v0.7.3, /releases/tag/v0.7.3rc1, /releases/tag/v0.7.3.dev2, /issues/4561
- https://github.com/incoai/splash/releases/tag/1.4.1, /releases/tag/1.5.0, /issues/471
- https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0, /pull/30965, /pull/30663, /pull/31506, /issues/30726, /pull/30680, /pull/30982
- https://pypi.org/project/mlx/, https://pypi.org/project/mlx-lm/, https://github.com/ml-explore/mlx-lm/pull/1788
- https://github.com/youssofal/MTPLX
- https://lmstudio.ai/changelog/lmstudio, https://lmstudio.ai/changelog
- https://github.com/ollama/ollama/releases/tag/v0.40.14
- https://huggingface.co/Qwen, https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GSQ-RCO-GGUF
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- https://github.com/anomalyco/opencode/releases/tag/v2.2.0, /releases/tag/v1.19.5
- https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.6
- https://github.com/charmbracelet/crush/releases/tag/v0.99.0
- https://www.reddit.com/r/LocalLLaMA/comments/1xif6lf/apsara_conference_qwen4_next_week/
- https://www.ithinkdiff.com/macos-tahoe-26-7-2-macos-sequoia-15-8-2-security-updates/

Adendo de 04/11:

- https://github.com/ddalcu/mlx-serve/pull/1075, /pull/1081, /issues/1004
- https://github.com/jundot/omlx/releases/tag/v0.7.4.dev1, /pull/4902, /pull/5012
- https://github.com/ggml-org/llama.cpp/releases/tag/v0.9.0, /pull/31443, /pull/30141, /pull/29510
- https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF
- https://github.com/anthropics/claude-code/releases/tag/v2.1.318
- https://github.com/NousResearch/hermes-agent/releases/tag/v0.22.7
- https://github.com/ollama/ollama/releases/tag/v0.40.15-rc0
- https://www.reddit.com/r/LocalLLaMA/comments/1xnvbxn/new_qwen38flashnext_unsloth_dynamic_v31_ggufs/
- https://www.reddit.com/r/LocalLLaMA/comments/1xnrhvb/kimik31pro_is_now_openweights/

Adendo de 05/11:

- https://github.com/ddalcu/mlx-serve/blob/main/CHANGELOG.md, /blob/main/benchmarks.md, /commit/ac064dd133369e146931039e12dbc3489462c9a7, /pull/1094, /issues/1090, /issues/844
- https://github.com/ggml-org/llama.cpp/pull/30982, /pull/31688, /pull/31660, /pull/30137, /pull/30541, /releases/tag/b12128
- https://github.com/jundot/omlx/pull/4866, /pull/5082
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/commit/7ecef55, https://huggingface.co/Qwen/Qwen3.8-27B/commit/8c0b3d3
- https://huggingface.co/austindixson/Qwen3.8-Flash-Next-Unsloth-V3.1-MLX
- https://www.reddit.com/r/LocalLLaMA/comments/1xomy0i/guide_qwen38_flashnext_on_a_single_rtx_5080_64gb/

Adendo de 06/11:

- https://github.com/ddalcu/mlx-serve/releases/tag/v26.11.2, /commit/0bfdff0, /blob/v26.11.2/CHANGELOG.md
- https://github.com/ml-explore/mlx/commit/a59cc23, /blob/main/docs/src/usage/environment_variables.rst
- https://github.com/incoai/splash/releases/tag/1.6.0, /blob/1.6.0/docs/release-notes/1.6.0.md, /issues/644
- https://github.com/ggml-org/llama.cpp/pull/31233, /pull/30966, /pull/31692, /pull/31589, /releases/tag/b12177
- https://github.com/jundot/omlx/issues/4561
- https://github.com/anthropics/claude-code/releases/tag/v2.1.319
- https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0
- https://github.com/charmbracelet/crush/releases/tag/v0.100.0, https://github.com/openai/codex/releases/tag/rust-v0.167.0
- https://huggingface.co/ricursiveAI/Ripple-65B-Preview, https://huggingface.co/Qwen
- https://www.reddit.com/r/LocalLLaMA/comments/1xpjzve/contrary_to_what_the_hype_train_may_suggest_qwen4/, https://www.reddit.com/r/LocalLLaMA/comments/1xphi5w/ripple_65b_preview_vs_qwen_38_27b_vs_qwen_38/
