# Stacks do rig: o que mudou entre 06/11 e 11/11/2026

**O Splash 1.6.1 saiu em 11/11 e muda a memória justamente onde a 1.6.0 perdeu no rig.** A campanha [splash16](../bench/splash16-2026-11/results/summary.md) manteve o launcher na 1.5.0, porque duas sessões de 256K ficaram até 65% mais lentas na 1.6.0 por espera de memória. A 1.6.1 muda essa espera, muda o staging de experts em GPUs M4 Max e passa a ler a tabela PLE do Flash-Next do SSD por padrão. Nenhuma fonte traz número dessa release num M4 Max. O mlx-serve não teve release nova, e a 26.11.2 continua sem teste no rig. O MLX, o mlx-lm e os pesos da Qwen não mudaram.

**Procedência.** A nota junta buscas de 11/11 até 17:00 UTC pela API do GitHub, pela API do Hugging Face, pelo PyPI e pelo r/LocalLLaMA. A linha de base é [`rig-stack-updates-20261103.md`](rig-stack-updates-20261103.md) até o adendo de 06/11, mais o que as campanhas de 08/11 a 10/11 instalaram. As versões do rig vêm de `ls ~/.local/opt/qwen38/` e `ps` por SSH em 11/11. As marcas seguem as notas anteriores: **fabricante** é a Qwen, **terceiro** cobre release, issue, PR, card no HF e Reddit, e **medido-no-rig** vem das campanhas deste repo. Nenhum teste rodou para esta nota.

## Resumo por stack

| Stack | No rig em 11/11 | Último em 11/11 | Impacto no rig |
|---|---|---|---|
| Splash | 1.5.0 na porta 8585 (`k2f`); 1.6.0 instalado | **1.6.1** (11/11) | Muda a espera de memória da 1.6.0, o staging de experts no M4 Max e a PLE (teste 1) |
| mlx-serve | 26.10.3 (driver diário) | 26.11.2 (06/11); `main` com ~40 commits | Nenhuma release nova; a `main` conta tokens de thinking no `usage` (teste 2) |
| oMLX | 0.7.2 | 0.7.3; `main` com ~40 commits | Nenhuma release; scheduler de concorrência novo na `main` |
| llama.cpp | b11569, b11609 | v0.9.0 (04/11); builds até **b12284** | Três correções de Metal, nenhuma ligada ao Flash-Next |
| MLX core e mlx-lm | — | 0.32.4 e 0.32.2 no PyPI | Nenhum |
| MTPLX | 2.12.2 | **2.12.3** (06/11) | Prompt cache do Flash-Next volta a funcionar; continua fora do plano |
| Ollama | não instalado | **0.40.16** (09/11) | Flash-Next com ~27 GiB a menos de memória no Apple silicon |
| Modelos Qwen | Flash-Next e 27B sem uso direto dos SHAs | Flash-Next `812d96e`, 27B `3756181` (07/11) | Só metadados do template; o texto renderizado não muda |
| Packs da campanha | Swift 1.5 GGUF `0142554` | sem mudança | Nenhum |
| Claude Code | 2.1.292 (rig, sem conferir em 11/11) | **2.1.322** (10/11) | Nada novo contra servidor local |
| Outros harnesses | OpenCode 1.18.31, Hermes 0.21.2 (MacBook) | OpenCode **2.2.7**, Hermes **0.23.1**, Codex **0.167.1** | Nenhum direto |
| macOS | 26.6.2 | sem conferir | — |

## Splash 1.6.1

Fontes: [release](https://github.com/incoai/splash/releases/tag/1.6.1) e [notas detalhadas](https://github.com/incoai/splash/blob/1.6.1/docs/release-notes/1.6.1.md). Todos os números são **terceiro**, e nenhum é de M4 Max.

**Memória.** Estes itens tocam a espera de memória que a splash16 mediu na 1.6.0:

- Uma lane com páginas copiadas no SSD mantém essas páginas na RAM até que um claim precise delas. Num Mac com espaço livre, nenhum KV volta do SSD.
- Um prompt longo não falha mais no meio por falta de memória. O início espera as lanes em execução ou é recusado, com uma mensagem que diz o que falta.
- Dois requests longos e distintos no limite de memória terminam, como cada um termina sozinho.
- Um claim atendido pelo cache, ou que espera menos de 1 s, não gera mais linha de log.
- As notas citam a #713 nesses itens. A #713 descreve outro caso: num Mac de 64 GB, o piso do store de experts fica em 100% e todo request acima de ~30K tokens falha com `capacity_exhausted`. A issue continua aberta em 11/11.

**Mudanças que tocam o M4 Max do rig:**

- **Staging de experts.** GPUs M3 e M4 Pro e Max com mais de 10 cores agora fazem staging dos experts de MoE, como as outras GPUs. O decode de uma linha passa a depender do batch. O M4 Max do rig tem 40 cores.
- **PLE do Flash-Next.** O padrão `--ple-memory auto` lê a tabela PLE de 28.8 GB por um cache de linhas de até 237 MiB, em vez de carregar a tabela inteira. Isso libera memória para KV e cache. `--ple-memory off` mantém a tabela na RAM. Num M5 Pro, o `off` dá o primeiro token 0.6 s antes a 6K tokens.
- **Kernels antes do Ready.** A #715 fecha um travamento de request curto em GPUs Apple9 com mais de 10 cores. O M4 é Apple9. Agora o servidor cria todos os kernels de prefill antes do Ready, e um request longo não espera mais por um kernel.
- **Velocidade:** o decode de MoE em streaming fica de 8% a 17% mais rápido no Flash-Next a 16G e 8G. O TTFT cai 8% a 128K e de 11% a 12.5% a 256K. Os ganhos de `--activations auto` valem só para M5 ou mais novo.

**Mudanças que podem quebrar:**

- Um servidor cujo engine para de vez sai com exit 69. A 1.6.0 continuava no ar e respondia 500. Os launchers do repo não usam supervisor com `KeepAlive`.
- As linhas de log de um request agora levam o número do request: `Done · request N · …`. O regex `DONE` de `bench/flashnext-concurrency-2026-10/scripts/claude_requests.py:26` espera `Done · input` logo depois do horário, então ele deixa de casar com o log da 1.6.1. A nota não conferiu o formato exato da linha nova.
- O `/status` continua no schema 8 e ganha campos: `console.dropped_lines`, `kv_spill.releases` e `metal.pipelines_created_while_serving`.
- Um update apaga do cache do HF os arquivos do commit anterior que nenhum outro snapshot usa. Um `--revision` antigo baixa os arquivos de novo.
- GGUFs com `general.alignment` abaixo de 8 são recusados. A nota não conferiu esse valor no pack do rig.
- Um cliente que para de responder perde a lane 60 s depois do último dado. Uma quarentena de engine dura uma hora acordado, não até o restart.

**Correção de segurança.** Com `http_proxy` definido, o launcher da 1.5.0 envia a API key do servidor ao proxy. A 1.6.0 e a 1.6.1 corrigem isso. O rig ainda roda a 1.5.0 na porta 8585. Por SSH em 11/11, nenhuma variável `*_proxy` aparece no ambiente, nos arquivos `~/.zshrc`, `~/.zprofile` e `~/.zshenv`, nem no `launchctl`. A nota não conferiu o shell interativo nem o proxy do sistema.

## mlx-serve, `main` depois da 26.11.2

Não saiu release desde a v26.11.2 de 06/11. Itens da `main` que tocam o driver diário:

- **#1113** e **#1122:** o `usage` passa a trazer os tokens de thinking. O caminho Anthropic usa `output_tokens_details.thinking_tokens`, e o caminho chat usa `reasoning_tokens` em streaming e em tool calls. Isso ajuda o teste 10 da nota de 03/11, que conta tokens de raciocínio.
- **#1151:** a residência em memória passa a contar slots na fila e o cache da cabeça MTP de cada request.
- **#1116:** a atenção de decode com KV empacotado roda nas unidades simdgroup-matrix.
- **#1153** (fechada em 09/11): com `tool_choice: "required"` e um prompt fora do assunto, o Flash-Next na 26.11.2 devolvia `function.name` igual a `"call"`. O commit `f3b203a` corrige o caso com uma ferramenta declarada.
- Issues novas na 26.11.2: **#1163**, um SIGSEGV em `logSpecStats` quando um slot é cancelado. **#1127**, o cálculo de "o modelo cabe na RAM" erra. A nota não conferiu se esses casos atingem o Flash-Next.

## oMLX, llama.cpp e outros runtimes

**oMLX.** Sem release. A `main` tem ~40 commits de 10/11 e 11/11. Entre eles, a **#5164** adiciona prioridade entre requests concorrentes, com um modo Balanced adaptativo. A **#5165** mantém o limite wired do Metal quando um batch fecha. A **#5160** e a **#5175** deixam um request novo entrar no fim do chunk de prefill em execução. A **#5089** muda o qwen4-exp em GPUs g13 e g14.

**llama.cpp, builds b12178 a b12284.** Não saiu estável nova; a última é a v0.9.0, de 04/11. Itens de Metal: a **#31662** impede escrita fora dos limites no buffer de saída de flash attention, a **#30711** muda o `ggml_tri`, e a **#31852** corrige o `GROUP_NORM`. A **#31927** faz o MTP ler os hidden states de um buffer no device. A **#30726**, sobre pausas de minutos no Metal com o qwen4exp, segue aberta sem atividade desde 17/10.

**MTPLX 2.12.3.** Corrige o prompt cache do Flash-Next no OpenCode e em clientes de API. Na 2.12.2, cada turno lia a conversa inteira de novo. Também corrige um HTTP 500 depois de compactação e o erro 409 com vários subagentes do Claude Code. O MTPLX continua fora do plano do rig.

**Ollama 0.40.16.** O Flash-Next usa cerca de 27 GiB a menos de memória no Apple silicon. A release não diz como, e a nota não conferiu se é a mesma leitura da PLE do SSD.

## Modelos e harnesses

**Qwen.** Em 07/11, o Flash-Next (`812d96e`) e o 27B (`3756181`) ganharam um `response_template` no `tokenizer_config.json` e tags `{% generation %}` no chat template ([#81](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/81)). A nota comparou o `chat_template.jinja` de `7ecef55` e `812d96e`: o texto renderizado é o mesmo. Os pesos não mudaram. O Qwen4 segue sem pesos: o modelo mais novo da Qwen no HF ainda é o Qwen-Image-2.1-Turbo, de 09/10. Posts no r/LocalLLaMA falam do Qwen4 "nesta semana", sem fonte oficial.

**Packs.** O Swift 1.5 GGUF segue em `0142554`. O repo da Unsloth segue em `084c631`, e os commits de 07/11 só mudam o README. Os repos novos de Flash-Next no HF de 09/11 a 11/11 são quase todos NVFP4, abliterated ou quants para NVIDIA. A nota não leu os cards.

**Reddit.** A Apple prepara um app chamado Harbor que serve modelos open-weight num Mac e junta Macs por Thunderbolt 5 ([post](https://www.reddit.com/r/LocalLLaMA/comments/1xszbe7/apple_has_new_mac_app_coming_to_make_running/)). Não há release nem data. A Z.ai anunciou o GLM-5.5 em 32B, 122B e 256B, sem pesos. O tencent/Qwen3.8-27B-DSpine-b16 é um draft para o 27B, e a #731 do Splash adiciona suporte experimental a ele.

**Harnesses.** O Claude Code 2.1.321 e o 2.1.322 não mudam nada contra um `ANTHROPIC_BASE_URL` local, pelas notas. O 2.1.320 não tem release no GitHub. O OpenCode 2.2.6 e o 2.2.7 corrigem providers custom: um provider legado com `limit` parcial não some mais, e um config v1 com `api` e `options.baseURL` mantém o `baseURL`. O Hermes 0.23.1 e o Codex 0.167.1 não citam provider local.

## Testes sugeridos

1. **Splash 1.6.1 contra a 1.5.0** com o Swift 1.5 `IQ4_XS` (`k2f`): repetir o teste das duas sessões de 256K e o de sessões do Claude Code a 128K da [splash16](../bench/splash16-2026-11/results/summary.md). Rodar a 1.6.1 com `--ple-memory auto` e com `off`, porque o padrão mudou. Descartar a primeira execução, por causa do warm-up. Conferir antes se o GGUF carrega e ajustar o regex `DONE` do `claude_requests.py`. A regra "Trocar o launcher" da splash16 decide.
2. **mlx-serve 26.11.2 contra a 26.10.3:** é a campanha dos testes 7, 8 e 9 da [campanha de pesos](../bench/flashnext-weights-2026-11/results/summary.md). Ela continua válida. Se a `main` sair numa release antes da campanha, usar a release nova, porque o `usage` com tokens de thinking simplifica o teste de thinking.
3. **Shell interativo do rig:** conferir se algum proxy fica definido nele enquanto o Splash 1.5.0 roda. Se ficar, trocar a API key do servidor.

## Fontes

- https://github.com/incoai/splash/releases/tag/1.6.1, /blob/1.6.1/docs/release-notes/1.6.1.md, /issues/713, /issues/715, /issues/644, /pull/731
- https://github.com/ddalcu/mlx-serve/blob/main/CHANGELOG.md, /pull/1113, /pull/1122, /pull/1151, /pull/1116, /issues/1153, /issues/1163, /issues/1127
- https://github.com/jundot/omlx/pull/5164, /pull/5165, /pull/5160, /pull/5175, /pull/5089
- https://github.com/ggml-org/llama.cpp/releases/tag/b12284, /pull/31662, /pull/30711, /pull/31852, /pull/31927, /issues/30726
- https://github.com/youssofal/MTPLX/releases/tag/v2.12.3
- https://github.com/ollama/ollama/releases/tag/v0.40.16
- https://pypi.org/project/mlx/, https://pypi.org/project/mlx-lm/
- https://huggingface.co/Qwen/Qwen3.8-Flash-Next/commit/812d96e, https://huggingface.co/Qwen/Qwen3.8-27B/commit/3756181, https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/81
- https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF, https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF
- https://github.com/anthropics/claude-code/releases/tag/v2.1.321, /releases/tag/v2.1.322
- https://github.com/anomalyco/opencode/releases/tag/v2.2.6, /releases/tag/v2.2.7
- https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.1, https://github.com/openai/codex/releases/tag/rust-v0.167.1
- https://www.reddit.com/r/LocalLLaMA/comments/1xszbe7/apple_has_new_mac_app_coming_to_make_running/, https://www.reddit.com/r/LocalLLaMA/comments/1xossr5/zai_chief_scientist_jie_tang_just_revealed_the/, https://www.reddit.com/r/LocalLLaMA/comments/1xr2aaa/tencentqwen3827bdspineb16_hugging_face/
