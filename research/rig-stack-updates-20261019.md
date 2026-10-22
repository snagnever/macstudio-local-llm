# Stacks do rig: o que mudou entre 14 e 19/10/2026

Nenhuma mudança da janela pede trocar o driver diário. O Swift 1.5 no **mlx-serve 26.10.1** continua a configuração certa. O mlx-serve não lançou versão nova, e a issue #912 relata uma regressão de tool calls na 26.10.2 que a 26.10.1 não tem, num M4 Max 64 GB (**terceiro**). Isso é motivo para adiar a troca do driver para a 26.10.2. A Qwen não mexeu em nenhum modelo, e nenhum pack que o rig usa mudou de bytes (**fabricante**, **terceiro**). Três mudanças pedem ação na campanha `bench/flashnext-next-steps-2026-10`. A primeira: o umixer v2 virou tombstone, e o `fetch_pack.py` do braço `x1` precisa apontar para o repo sem `-v2`. A segunda: o **oMLX 0.7.1rc1** substitui o 0.7.1.dev1 nos braços oMLX. A terceira: o **llama.cpp b11738** ou posterior substitui o b11609 na Task 8, porque corrige uma corrida no Metal que dava saída errada em modelos MoE. Os scripts do rig já passam `--port` ao llama-server, então a mudança da porta padrão na v0.7.0 não quebra nada.

**Procedência.** O relatório junta quatro buscas na web de 19/10, feitas pela API do GitHub, pela API do Hugging Face, pelo PyPI e pelo Reddit. A linha de base é [`qwen38-flashnext-updates-20261014.md`](qwen38-flashnext-updates-20261014.md). Cada número leva uma marca. **fabricante** é a Qwen. **terceiro** cobre release, issue, PR, card no HF e Reddit. **medido-no-rig** vem das campanhas deste repo. Nenhum teste rodou para este relatório, e nenhuma fonte da janela traz número de Flash-Next medido num M4 Max. Números de M5 não valem para o M4 Max: a NAX e as unidades tensoriais existem só no M5.

## Resumo por stack

| Stack | Em 14/10 | Em 19/10 | Impacto no rig |
|---|---|---|---|
| mlx-serve | v26.10.2 estável | v26.10.2 (sem release); `main` com correções de cache SSD | Manter 26.10.1 no driver até a #912 fechar |
| Splash | 1.3.1 | **1.3.2** (14/10) | Adiar: regressão de cache em greedy (#483) |
| llama.cpp | b11609, estável v0.6.0 | **b11739**, estável **v0.7.0** (15/10) | Task 8 em b11738+; porta padrão agora 9931 |
| oMLX | 0.7.1.dev1 | **0.7.1.dev2** e **0.7.1rc1** (15/10) | Braços oMLX em rc1; janela ≤ 262144 |
| MLX core | 0.32.3 | **0.32.4** (14/10) | Chega ao rig pelo oMLX rc1 |
| mlx-lm | sem `qwen4_exp` | 0.32.2; PR #1788 ainda parada | Nenhum |
| MTPLX | 2.12.2 | 2.12.2 (sem commits) | Nenhum; bugs de restore em aberto |
| LM Studio | 0.4.26 | 0.4.26 | Nenhum |
| Ollama | — | 0.40.6 / 0.40.7-rc0, sem Flash-Next | Nenhum |
| Modelos Qwen | Flash-Next `de4b8e4` | sem mudança | Nenhum |
| Packs da campanha | ver nota de 14/10 | só o umixer mudou de repo | Corrigir o repo do braço `x1` |

## mlx-serve: nenhuma release, e a 26.10.2 ganhou uma regressão de tool calls

A última release continua a **v26.10.2** (12/10). A seção sem release do CHANGELOG traz o título "v26.10.2 — New Models, Transcripts, RDMA, Faster", que reusa o número por engano. O commit 8721c1d (13/10) se chama "26.10.3 release validation" (**terceiro**, [CHANGELOG](https://github.com/ddalcu/mlx-serve/blob/main/CHANGELOG.md)).

A `main` acumulou correções que tocam o caminho híbrido do Flash-Next:

- **c24807e** (16/10): o flush ocioso salva no SSD todas as sessões pendentes, não só a mais nova. O SIGTERM salva as fatias pendentes antes de sair, com limite em `--shutdown-persist-secs` (0 mantém o comportamento antigo). Isso ajuda sessões longas que atravessam um reinício do driver ([commit](https://github.com/ddalcu/mlx-serve/commit/c24807e)).
- **PR #882** (17/10): corrige um double free (SIGABRT) no append só-SSM do cache em disco quando a escrita do meta falha. Modelos GDN como o Flash-Next passam por esse caminho ([PR #882](https://github.com/ddalcu/mlx-serve/pull/882)).
- **PR #795** (16/10): a chave do cache SSD inclui a mídia. Só importa para turnos com imagem ([PR #795](https://github.com/ddalcu/mlx-serve/pull/795)).
- **PR #880** (17/10): carrega o `nvidia/Qwen3.8-Flash-Next-FP4-Local`. O GEMV MXFP8 novo é "~22% faster than MLX's at decode on M4", mas só nas camadas MXFP8, então não toca o pack 4.7bpw. No M5 Ultra o pack FP4 faz prefill a 5340 tok/s contra 5387 do iQ-MLX-4.7bpw (**terceiro**, [PR #880](https://github.com/ddalcu/mlx-serve/pull/880)).
- A PR #884 (admissão de request curto durante prefill longo) pula o `qwen4_exp`. As PRs #874, #891 e #881 valem só para o M5. A PR #895 distribui o Flash-Next em dois Macs.

Situação das issues que a nota de 14/10 acompanhava:

- **#831** (loops com `--mtp-typical 0.2 --mtp-greedy-tail`) fechou em 15/10 como comportamento esperado, sem fix. O autor não viu loops com `--mtp-typical 0.1` ([issue #831](https://github.com/ddalcu/mlx-serve/issues/831)).
- **#837** (MTP do ds4 armada apesar de `--no-mtp`) fechou em 16/10 com o commit 8721c1d.
- **#838** (rpath do Homebrew) fechou em 16/10 com o commit a9859df.
- **#844** (modo só-SSD recusa turno quente) segue aberta, sem atividade.

Duas issues novas pesam para o rig. A **#912** (18/10, aberta) é uma regressão da 26.10.2 com o harness Crush: tool calls chegam truncadas e a execução para. A 26.10.1 não tem o problema. O relato vem de um Qwen3.8-27B 4-bit num **M4 Max 64 GB** e num M2 Max. Ninguém testou o Flash-Next (**terceiro**, [issue #912](https://github.com/ddalcu/mlx-serve/issues/912)). A **#853** (14/10, aberta) mede o 27B a 128K num **Mac Studio M4 Max 128 GB**, ou seja, numa máquina igual ao rig. O drafter DFlash2 padrão fica mais lento que o MTP sozinho (**terceiro**, [issue #853](https://github.com/ddalcu/mlx-serve/issues/853)):

| Pack 27B | drafter padrão (prosa / código / recall, tok/s) | `--no-drafter` |
|---|---|---|
| 4-bit | 9.9 / 18.1 / 11.6 | 19.1 / 26.0 / 23.5 |
| 8-bit | 6.8 / 13.0 / 10.6 | 13.2 / 22.2 / 16.3 |

Isso concorda com o `r27d` da campanha do 27B, que caiu para 15.1 tok/s a 128K com o DFlash2 (**medido-no-rig**, `bench/qwen38-27b-next-steps-2026-10/results/summary.md`). Se o 27B voltar ao mlx-serve, o braço deve rodar com `--no-drafter`.

## Splash 1.3.2: cache SSD ligado por padrão e uma regressão de determinismo

O **Splash 1.3.2** saiu em 14/10 (**terceiro**, [release](https://github.com/incoai/splash/releases/tag/1.3.2)). As mudanças que importam para o 27B no rig:

- O cache de prefixo em SSD fica ligado por padrão, com cota automática "up to 32 GiB". `--max-cache-disk 0` desliga. As notas avisam que isso "may advertise a smaller automatic context".
- O `--state-format bf16` novo reduz o estado GDN em cache do 27B de 153 para 81 MiB.
- `thinking_token_budget`, `--thinking-token-budget` e `--thinking-end-text` são novos.
- O protocolo passa de 8 para 10, então o servidor precisa de reinício após o upgrade.
- Os ganhos citados (TTFT ~37 ms menor, follow-up 11–14% mais rápido num prefixo de 8K) vêm de um **M5 Max**.

Três issues contra a 1.3.2 desaconselham trocar o `k27` agora. A **#483** (19/10) mostra respostas greedy diferentes quando o prompt vem do cache de prefixo; a 1.3.1 não tem o defeito ([issue #483](https://github.com/incoai/splash/issues/483)). A **#446** limita um `--max-cache-disk` explícito a um quarto do espaço livre. A **#441** mede decode ~2% mais lento que a 1.2.0 em alvos MLX 4-bit, num M5 Max. O suporte a Flash-Next no Splash é uma pilha de 21 PRs abertas (#449–#469, MTP em #448) que aceita só GGUF. A issue #471 relata que o Swift 1.5 MLX não carrega no Splash por causa da torre de visão quantizada ([PR #467](https://github.com/incoai/splash/pull/467)).

## llama.cpp v0.7.0 e b11738: um fix de MoE no Metal e uma porta nova

A **v0.7.0** saiu em 15/10 e é a primeira estável desde a v0.6.0. Ela aponta para o b11669 e já contém o b11575, o b11588 e o b11600, inclusive o fix dos 27 GiB da tabela PLE. Duas mudanças quebram compatibilidade: a porta padrão do servidor passa a **9931** (PR #30159), e a saída do chat vira um array de partes (PR #30389) (**terceiro**, [v0.7.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0)). Os scripts do rig passam `--port` explícito, por exemplo `--port 8080` em `bench/flashnext-next-steps-2026-10/scripts/run-llama-flashnext.sh`, então a porta nova não os afeta.

O build mais recente é o **b11739** (19/10). Os builds depois do b11609 que importam:

- **b11738**: corrige uma corrida na fusão `moe_reduce` do Metal que causava "rare non-deterministic wrong results" em MoE ([PR #30795](https://github.com/ggml-org/llama.cpp/pull/30795)). Isso vale para o Flash-Next e o qwen3-coder-next. O mesmo build impede restaurar checkpoint SWA de um prompt não relacionado ([PR #30666](https://github.com/ggml-org/llama.cpp/pull/30666)) e troca o cache LRU de experts por SLRU ([PR #30637](https://github.com/ggml-org/llama.cpp/pull/30637)).
- **b11645**: o KV simples respeita PARTIAL_ONLY, e a cabeça MTP do Qwen3.8 para de copiar o KV inteiro em cada checkpoint. A PR estima "about 1.2 GiB per checkpoint at 262k" no 27B com draft-mtp ([PR #30514](https://github.com/ggml-org/llama.cpp/pull/30514)). O kernel BF16 de flash attention do mesmo build (1.7–2.5× num M5 Pro, [PR #30491](https://github.com/ggml-org/llama.cpp/pull/30491)) usa a Tensor API e provavelmente não ajuda o M4 Max. Isso não foi verificado.
- **b11630**: `--spec-draft-n-ubatch` separa o ubatch do contexto de draft e reduz a memória com draft-mtp ([PR #30459](https://github.com/ggml-org/llama.cpp/pull/30459)).
- **b11669**: correções de reuso do prompt cache para SWA (Gemma 4) e para MTP (PRs #30580, #30574, #30567, #30498).

A issue **#30726** (17/10) relata prefill do qwen4exp travado por minutos com `-c 262144` no Metal, num M5 Ultra 256 GB. É intermitente, e o ggerganov não reproduziu num M5 Max ([issue #30726](https://github.com/ggml-org/llama.cpp/issues/30726)). A Task 8 deve registrar o TTFT de cada rep a 256K para detectar esse efeito. A issue **#30368** (`draft-mtp` + `--kv-unified` + `--parallel >1`) segue aberta e sem fix. O braço `g1` não usa essa combinação. A fusão `hc_post` do qwen4exp entrou só no CUDA (b11721); o port Metal é a PR #30680, aberta, com "~1.1% TG on M2 Ultra".

## oMLX 0.7.1rc1: MLX 0.32.4 e as correções do Flash-Next que estavam na main

O **0.7.1.dev2** e o **0.7.1rc1** saíram em 15/10, com dez horas de diferença (**terceiro**, [rc1](https://github.com/jundot/omlx/releases/tag/v0.7.1rc1)). O rc1 traz:

- **MLX 0.32.4** (PR #4550). Uma instalação a partir do código precisa repetir `make install`. Sem isso, os kernels nativos compilados para o MLX antigo caem em caminhos mais lentos. O `requires-python` continua `>=3.11,<3.14`.
- As correções do Flash-Next que a nota de 14/10 viu na `main`: estado GDN exato em prefill com padding (PR #4526), menos memória de prefill em packs fp16 e o "Qwen4 Extended Fused Decode" nas configurações do modelo (commit 3c39990).
- Leituras PLE mais rápidas e projeções de verify 8-bit largas (PRs #4464, #4472, #4475), sem números.
- **O YaRN liga em todo prompt quando a janela de um modelo da família Qwen3.5 passa de 262144** (PR #4445). Os braços oMLX devem manter a janela em 262144.
- Requests ficam pausados, não abortados, sob pressão de memória (PR #4509).
- Os defaults de amostragem passam a vir do `generation_config.json` (PR #4416). Os braços que dependem de temp 1.0 / top_p 0.95 / top_k 20 devem passar esses valores no request para não mudar de configuração em silêncio.
- O Splash pode servir como engine externo para o Qwen3.8 dentro do oMLX, citando execuções em M4 Max na issue #4154.

Depois do rc1, a `main` recebeu a **PR #4648** (19/10): o MTP Lightning do Flash-Next passa a profundidade 1 por padrão. Num **M5 Max 128 GB**, o modo adaptativo deu "64-93 tok/s" e a profundidade fixa 1 deu "87-98 tok/s" ([PR #4648](https://github.com/jundot/omlx/pull/4648)). A PR #3963 dá um buffer de capacidade ao indexer do `BatchQSAKVCache` do `qwen4_exp`. Nenhuma das duas tem tag.

A issue **#4561** (aberta) relata que, no dev2, o Prefill Memory Guard rejeita requests longos do Flash-Next num **M3 Max 128 GB**. O mantenedor não vê diferença entre dev1 e dev2 num M3 Ultra e suspeita de um cache quente cheio. Outro usuário, com 256 GB, vê o `process_memory_enforcer` encerrar o processo a "~197k tokens" ([issue #4561](https://github.com/jundot/omlx/issues/4561)). Isso afeta diretamente as bandas de 256K das Tasks 5 e 7 num rig de 128 GB. A banda deve registrar a recusa do guard como resultado, não como falha do probe.

## MLX, mlx-lm e MTPLX

O **MLX 0.32.4** saiu em 14/10 com 97 commits sobre a 0.32.3 ([release](https://github.com/ml-explore/mlx/releases/tag/v0.32.4)). Ele inclui as correções de split-K quantizado que a nota anterior viu na `main`. Na PR #4641, os parciais passam a float32, e o erro médio cai de "~1.5–3x" o baseline para ~1× ([PR #4641](https://github.com/ml-explore/mlx/pull/4641)). A **PR #4633** cria a variável `MLX_METAL_RESIDENCY_REFRESH_INTERVAL_MS`, que impede que páginas sejam desfixadas após ~2 s de GPU ociosa. Num M5 Pro 64 GB, a PR mede ~300 ms de atraso no primeiro request sem pressão de memória e ~2 s com pressão ([PR #4633](https://github.com/ml-explore/mlx/pull/4633)). O mlx-serve embute o próprio MLX (0.32.3 na 26.10.2), então essa variável só chega ao driver quando o mlx-serve trocar o pin. A `main` do MLX já está em 0.32.5, sem release, com correções para M1/M2 e para buffers acima de 2^31 elementos.

O **mlx-lm** lançou 0.32.1 (15/10) e 0.32.2 (16/10), sem nada para o rig. A PR #1788 (`qwen4_exp`) segue parada desde 04/10 ([PR #1788](https://github.com/ml-explore/mlx-lm/pull/1788)). No servidor, nada entrou. Há issues abertas sobre tool calls descartadas (#1972, #1946) e sobre o parser `qwen3_coder` truncando valores de parâmetros (#1992, #1993).

O **MTPLX** não tem commits desde 03/10 e continua no 2.12.2. A issue #624 (restore frio parcial) segue sem fix. Duas issues novas são defeitos de correção. A #635 mostra um restore de prefixo em SSD que instalou o estado recorrente de outra conversa, num M3 Ultra 256 GB. A #640 mostra todos os requests falhando com "[metal::malloc] Resource limit (499000) exceeded" após ~51 h de uptime ([issue #635](https://github.com/youssofal/MTPLX/issues/635), [issue #640](https://github.com/youssofal/MTPLX/issues/640)). O MTPLX continua fora do plano.

## LM Studio e Ollama: nada novo

O LM Studio continua no **0.4.26** (13/10), com runtime llama.cpp 2.50.0 (upstream b11337), e não tem beta aberto. O mlx-engine não teve commits desde 05/10 ([changelog](https://lmstudio.ai/changelog/lmstudio)). O Ollama lançou 0.40.5, 0.40.6 e 0.40.7-rc0, sem Flash-Next; a issue #18071 que pede o modelo segue aberta ([v0.40.5](https://github.com/ollama/ollama/releases/tag/v0.40.5)).

## Modelos e packs: o umixer mudou de repo

A Qwen não publicou nada novo. O `Qwen/Qwen3.8-Flash-Next` continua em `de4b8e4` (27/08), o 27B em `1d4bf0f` e o Qwen3-Coder-Next em `a7fbcb5` (**fabricante**). Não há Qwen4 com pesos.

Os packs da campanha:

- **Dankpaws Swift 1.5** continua em `13839b7`. Não existe Swift 1.6.
- **ddalcu iQ-MLX-4.7bpw** continua em `a0e89db`, com pesos de `dafff5c`.
- **Jundot oQ4e-mtp** continua em `c4ddfb5`.
- **ggml-org GGUF** foi para `92796c0` (19/10), mas só o README mudou. Os OIDs LFS do IQ4_NL e do MTP Q8_0 continuam os de `052beea`.
- **umixer v2** virou tombstone em `aad6f96` (14/10), sem pesos. Os mesmos bytes voltaram ao repo original, [`umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp`](https://huggingface.co/umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp), HEAD `73d2cd0`. Os 25 OIDs LFS são iguais aos do v2 em `ed5c722` (**terceiro**). O `plan.md` da campanha ainda baixa `umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp-v2` (linhas 84, 421 e 1379 de `bench/flashnext-next-steps-2026-10/plan.md`). Esse download agora traz só o card do tombstone.

Packs novos que cabem em 128 GB (todos **terceiro**, sem número de M4 Max):

- [`nace-ai/Qwen3.8-Flash-Next-MLX-4bit`](https://huggingface.co/nace-ai/Qwen3.8-Flash-Next-MLX-4bit) (18/10): MLX misto 4/6/8 para o engine Kapitsa. Declara KL de **0.129** contra o bf16, concordância top-1 de **86.8%**, PPL **4.109** (bf16 4.054) e ~73 GB na GPU. Não informa velocidade.
- [`Ecmcfee/Swift1.5-Qwen3.8-Flash-Next-q4-MTPLX`](https://huggingface.co/Ecmcfee/Swift1.5-Qwen3.8-Flash-Next-q4-MTPLX) (15/10): Swift 1.5 com a receita do MTPLX. Declara "AR 52.3 tok/s, MTP d3 110.5 / 104.8 tok/s" e ~83 GiB residentes num host de 128 GB sem chip nomeado. Não informa KLD, e o MTPLX está fora do plano.
- `scottlowry/Qwen3.8-Flash-Next-oQ4e-mtp`: card sem números.

Nenhum desses entra no plano agora. O nace-ai é o único com KLD publicado, mas depende de um engine que ainda não o suporta.

## Comunidade e harnesses

Nenhum relato da janela traz Flash-Next medido num M4 Max. Um post no r/LocalLLM compara o 27B num **M5 Pro 64 GB**: TensorFold 36.0, LM Studio 0.4.26 33.5, mlx-serve 26.10.2 30.1, Ollama 0.40.6 27.0 e oMLX 0.7.0 16.0 tok/s de decode (**terceiro**, [post](https://www.reddit.com/r/LocalLLM/comments/1xa2ae3/)). Dois engines novos apareceram, ijah e Kapitsa, sem números legíveis.

Os harnesses lançaram mudanças que afetam endpoints locais:

- **OpenCode 1.19.1–1.19.3** (15–16/10): as opções de reasoning na config geram variantes de reasoning, o compartilhamento de sessão foi descontinuado, e a 1.x não atualiza mais sozinha para a 2.x ([releases](https://github.com/anomalyco/opencode/releases)). Não foi possível confirmar uma release 2.x.
- **Hermes Agent 0.22.2** (15/10): substitui a 0.22.1, que saiu do commit errado. Requests locais passam a usar streaming sempre, e a compressão não estoura mais o timeout durante um prefill longo. A 0.22.0 adicionou reasoning effort por `/model X --reasoning high`, `cache_ttl: auto` opcional e a lista de tools congelada por sessão para o prompt cache ([releases](https://github.com/NousResearch/hermes-agent/releases)).
- **Cline 4.1.25** (16/10): modelos locais não falham mais com `BodyTimeoutError` após 5 min de prefill. A base URL OpenAI Compatible passa a ser usada exatamente como digitada, sem `/v1` implícito; URLs salvas são migradas uma vez ([releases](https://github.com/cline/cline/releases)).

## Ações para a campanha Flash-Next

1. Trocar o repo do braço `x1` para `umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp` no `plan.md` e no script, e registrar no recibo que os bytes são os do v2 `ed5c722`.
2. Instalar o oMLX 0.7.1rc1 num venv novo, com `make install` contra o MLX 0.32.4, e usá-lo nos braços `FR` e `FM`. Manter a janela em 262144 e passar a amostragem no request.
3. Usar o llama.cpp b11738 ou posterior na Task 8, no lugar do b11609. Manter `--port` explícito.
4. Manter o driver diário no mlx-serve 26.10.1 até a #912 ter diagnóstico. Antes de qualquer troca para a 26.10.2, rodar o probe de tool calls contra o Swift 1.5.
5. Manter o Splash 1.3.1 para o 27B até a #483 fechar.

## Fontes

Linha de base: [`research/qwen38-flashnext-updates-20261014.md`](qwen38-flashnext-updates-20261014.md).

Runtimes:

- https://github.com/ddalcu/mlx-serve/releases, /blob/main/CHANGELOG.md, /commit/c24807e
- https://github.com/ddalcu/mlx-serve/pull/795, /pull/880, /pull/882, /pull/884, /pull/895
- https://github.com/ddalcu/mlx-serve/issues/831, /issues/837, /issues/838, /issues/844, /issues/853, /issues/912
- https://github.com/incoai/splash/releases/tag/1.3.2, /issues/441, /issues/446, /issues/471, /issues/483, /pull/467
- https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0, /releases/tag/b11739
- https://github.com/ggml-org/llama.cpp/pull/30459, /pull/30491, /pull/30514, /pull/30580, /pull/30637, /pull/30666, /pull/30680, /pull/30795
- https://github.com/ggml-org/llama.cpp/issues/30368, /issues/30726
- https://github.com/jundot/omlx/releases/tag/v0.7.1rc1, /pull/4445, /pull/4550, /pull/4648, /issues/4561
- https://github.com/ml-explore/mlx/releases/tag/v0.32.4, /pull/4633, /pull/4641
- https://github.com/ml-explore/mlx-lm/pull/1788, /releases/tag/v0.32.2
- https://github.com/youssofal/MTPLX/issues/624, /issues/635, /issues/640
- https://lmstudio.ai/changelog/lmstudio
- https://github.com/ollama/ollama/releases/tag/v0.40.5

Pesos e comunidade:

- https://huggingface.co/Qwen/Qwen3.8-Flash-Next
- https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF
- https://huggingface.co/umixer/Qwen3.8-Flash-Next-oQ4e-mix6-mtp
- https://huggingface.co/nace-ai/Qwen3.8-Flash-Next-MLX-4bit
- https://huggingface.co/Ecmcfee/Swift1.5-Qwen3.8-Flash-Next-q4-MTPLX
- https://www.reddit.com/r/LocalLLM/comments/1xa2ae3/

Harnesses:

- https://github.com/anomalyco/opencode/releases
- https://github.com/NousResearch/hermes-agent/releases
- https://github.com/cline/cline/releases
