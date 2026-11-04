# Stacks do rig: o que mudou entre 22/10 e 03/11/2026

Três runtimes têm release nova que o rig ainda não instalou: **mlx-serve 26.11.1** (01/11), **oMLX 0.7.3** (31/10) e **llama.cpp v0.8.0** (28/10, primeira estável desde a v0.7.0). O Splash 1.4.1 e o 1.5.0 saíram na janela, e o rig já roda o 1.5.0. A Qwen não mudou nenhum peso. O Qwen4 pode sair nos próximos dias, mas não tem pesos nem data oficial. O Claude Code do rig (2.1.292) está 25 versões atrás, e cinco dessas versões mudam o comportamento contra um `ANTHROPIC_BASE_URL` local.

**Procedência.** A nota junta buscas de 03/11 pela API do GitHub, pela API do Hugging Face, pelo PyPI, pelo changelog do LM Studio, pelo Reddit e pela busca na web. A linha de base é [`rig-stack-updates-20261022.md`](rig-stack-updates-20261022.md), mais o que as campanhas de 23/10 a 02/11 instalaram. As versões instaladas no rig vêm de `ls ~/.local/opt/qwen38/` por SSH em 03/11. As marcas seguem as notas anteriores: **fabricante** é a Qwen, **terceiro** cobre release, issue, PR, card no HF e Reddit, e **medido-no-rig** vem das campanhas deste repo. Nenhum teste rodou para esta nota. Nenhuma fonte da janela traz número de Flash-Next medido num M4 Max. A nota não leu o card de cada pack novo do HF.

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

## Testes sugeridos

1. **mlx-serve 26.11.1 contra a 26.10.3** no Swift 1.5 (`w1z`): probe de tool calls com `frequency_penalty` 0 e `T_turno` a 32K e 128K. Conferir antes se o boot avisa sobre variáveis removidas.
2. **oMLX 0.7.3 contra a 0.7.2** nos braços `FR`/`FM`: `T_turno` com 1 stream e com 2 streams. O ganho publicado é de M3 Ultra e de batch, e a campanha de concorrência é onde ele apareceria.
3. **llama.cpp v0.8.0** com o GGUF do Flash-Next e o draft DFlash2 Q8_0, contra draft-mtp. É o teste 3 da nota de 22/10, que não rodou, agora numa estável.
4. **Claude Code 2.1.317 contra a 2.1.292** numa tarefa da `claude-code-concurrency-2026-11` no Splash 1.5.0: contar os requests com tool search e os retries 400/422 no proxy `request_log.py`.
5. **Task 5b da `splash-longctx-2026-10`**: o GSQ-RCO-Coder GGUF no Splash 1.4.1 ou posterior, se a campanha ainda não cobriu esse braço.

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
