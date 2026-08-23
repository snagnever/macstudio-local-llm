# 2026-08-21 — Qwen3.8-27B: prefix cache, prefill especulativo e runtime no M4 Max

> **Status:** infraestrutura base e preflight implementados. Os snapshots MLX 8-bit,
> GGUF Q4 e MTP foram baixados e verificados. Tentativas diagnósticas corrigiram o
> harness, mas ainda não há uma sessão canônica completa; oMLX e mlx-dspark aguardam
> implementação e execução dos braços descritos abaixo.

## Objetivo

Selecionar o setup de maior desempenho do Qwen3.8-27B no Mac Studio M4 Max com 128 GB.
Correção funcional é um gate eliminatório; entre os braços corretos, a campanha prioriza
tempo total, TTFT quente e throughput sustentado de decode em agent loops.

O teste deve responder estas perguntas:

1. O runtime reutiliza o prefixo em conversas append-only?
2. O runtime mantém o cache após tool calls?
3. MTP mantém o cache correto e reduz o tempo total?
4. MLX 8-bit supera o GGUF recomendado pela Unsloth e suas variantes Q6/Q8 no fluxo completo?
5. SpecPrefill reduz o tempo até o primeiro token sem perder contexto ou tool state?
6. O AWQ misto de 5,0 bpw supera os candidatos atuais no M4 Max?
7. O prefill pela Apple Neural Engine reduz a latência neste M4 Max?
8. Qual setup merece o Terminal-Bench completo?
9. DSpark ou DFlash 2 aumenta o decode e o tempo total frente ao mesmo target 8-bit sem especulação?

## Hardware e topologia

| Papel | Sistema | Uso |
|---|---|---|
| Rig | Mac Studio M4 Max, 128 GB, GPU de 40 núcleos | Serve o modelo e coleta telemetria |
| Driver | MacBook Pro | Envia probes e executa Harbor com Docker |
| Endpoint do rig | `macstudio.local` | Acesso pelo driver na rede local |

O driver não deve executar o modelo. O rig não deve executar Docker durante as medições de runtime.

## Hipóteses

| ID | Hipótese | Evidência necessária |
|---|---|---|
| H1 | MLX vence o GGUF no decode. | Decode medido com pesos comparáveis |
| H2 | MLX vence no tempo total somente com cache funcional. | Tempo até o primeiro token em turnos quentes |
| H3 | O Qwen híbrido reutiliza bem somente prefixes exatos. | Casos idêntico, append e mutação central |
| H4 | Tool calls podem invalidar o cache do `mlx-serve`. | Loop determinístico com 20 tool turns |
| H5 | MTP pode alterar a reutilização ou o estado do cache. | A/B cache ligado com MTP desligado e ligado |
| H6 | O `UD-Q4_K_XL` recomendado pela Unsloth oferece o melhor equilíbrio local. | Qualidade, memória e tempo total contra Q6 e Q8 |
| H7 | KV em 16-bit cabe no contexto padrão de 65.536. | Memória máxima sem swap |
| H8 | SpecPrefill reduz TTFT em contexto longo. | M/N contra L em 16K, 32K e 65K |
| H9 | O cache do oMLX preserva o system prompt durante SpecPrefill. | Prefixo estático e loop de ferramentas após cache hit |
| H10 | O AWQ misto de 5,0 bpw mantém qualidade com menos memória que MLX 8-bit. | Mesma tela de qualidade, memória e latência |
| H11 | O prefill pela ANE depende do hardware e precisa de ajuste local. | A/B com tuner no M4 Max e SpecPrefill desligado |
| H12 | DFlash 2 ou DSpark oferece o maior ganho de decode no target MLX 8-bit. | Baseline, DSpark e DFlash 2 explícitos no mesmo runtime e checkpoint |
| H13 | O ganho especulativo permanece positivo em contexto longo e após cache hit. | Decode e tempo total em 8K, 32K e 65K, separados por tipo de conteúdo |

## Escopo

### Incluído

- `mlx-serve` com MLX 8-bit.
- `llama.cpp` com Unsloth Dynamic v3 Q4 recomendado pelo vendor.
- Unsloth Dynamic v3 Q6 e Q8 como variantes de maior fidelidade.
- Cache frio, cache quente, append, mutação e restart.
- Tool calling com schemas estáveis.
- MTP nativo no MLX e `draft-mtp` no GGUF.
- `oMLX` com cache, MTP, SpecPrefill e prefill pela Apple Neural Engine (ANE).
- `mlx-dspark` com baseline, DSpark e DFlash 2 explícitos sobre o mesmo target 8-bit.
- `True2456/Qwen3.8-27B-AWQ-5.0bpw` somente no `oMLX`.
- Drafters `RadixArk/Qwen3.8-27B-DSpark` e `incoai/Qwen3.8-27B-DFlash2`.
- Drafts Qwen3.5-2B BF16 e Qwen3.5-0.8B BF16 para SpecPrefill.
- Contextos de 8.192, 32.768 e 65.536 tokens.
- Contexto de 16.384 tokens nos braços de prefill do `oMLX`.
- Tempo até o primeiro token, prefill, decode, memória e swap.
- Um subconjunto de qualidade antes do Terminal-Bench completo.

### Excluído

- Contexto acima de 65.536 na matriz principal. Cada braço aprovado e compatível com o contexto nativo recebe um smoke test em 262.144.
- YaRN e contexto de um milhão de tokens.
- Vision e processamento de vídeo.
- Batch com vários usuários.
- Lookup-only e tuning manual de draft cap antes da calibração automática do runtime.
- Uso do modelo AWQ fora do `oMLX`.
- Comparação direta entre resultados ANE de M3, M4 e M5.
- Quants Q3, Q2 e Q1.
- Ajuste fino e LoRA.

## Modelos candidatos

| ID da campanha | Modelo | Formato | Quant | Fase |
|---|---|---|---|---|
| `mlx8` | `ddalcu/Qwen3.8-27B-MLX-Serve-8bit` | MLX | 8-bit | Inicial |
| `gguf-q4` | `unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL` | GGUF | Dynamic v3 Q4 | Inicial, recomendado pela Unsloth |
| `gguf-q6` | `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL` | GGUF | Dynamic v3 Q6 | Após gate funcional do Q4 |
| `gguf-q8` | `unsloth/Qwen3.8-27B-GGUF:UD-Q8_K_XL` | GGUF | Dynamic v3 Q8 | Após gate funcional do Q4 |
| `awq5` | `True2456/Qwen3.8-27B-AWQ-5.0bpw` | MLX AWQ | 5,0 bpw misto | oMLX, após smoke do runtime |
| `draft-2b` | `Qwen/Qwen3.5-2B` | MLX BF16 | BF16 | SpecPrefill, keep 0,40 |
| `draft-08b` | `Qwen/Qwen3.5-0.8B` | MLX BF16 | BF16 | SpecPrefill, keep 0,50 |
| `mlx8-dspark` | `mlx-community/Qwen3.8-27B-8bit` | MLX | 8-bit, group size 64 | Target oficial da integração `mlx-dspark` |
| `draft-dspark` | `RadixArk/Qwen3.8-27B-DSpark` | MLX draft | 4-bit em memória pelo runtime | DSpark explícito |
| `draft-dflash2` | `incoai/Qwen3.8-27B-DFlash2` | MLX draft | 4-bit em memória pelo runtime | DFlash 2 explícito |
| `oq8e` | `Jundot/Qwen3.8-27B-oQ8e-mtp` | MLX oQ8e | 8,6 bpw efetivos, BF16 preservado | Candidato principal no M4; smoke pareado em 32K |
| `oq8e-fp16` | `Jundot/Qwen3.8-27B-oQ8e-fp16-mtp` | MLX oQ8e | 8,6 bpw efetivos, pesos auxiliares fp16 | Controle curto do artefato usado no benchmark público |

Fixe a revisão do Hugging Face antes de baixar cada modelo. Registre também o SHA-256 do artefato local.

| Artefato | Revisão verificada em 2026-08-21 |
|---|---|
| `Qwen/Qwen3.8-27B` | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| `ddalcu/Qwen3.8-27B-MLX-Serve-8bit` | `011e38296b3d2aa99245ed49a700459c4ac246b6` |
| `unsloth/Qwen3.8-27B-GGUF` | `4ca720788d1e01f1bff70c033e0d0028fd02e502` |
| `True2456/Qwen3.8-27B-AWQ-5.0bpw` | `dc699a76ddcbef44c188a8aee2ccc79ccc339a04` |
| `mlx-community/Qwen3.8-27B-8bit` | `815b83c0df8ffd1d1b5244cf75fd6ef14fca9ef9` |
| `RadixArk/Qwen3.8-27B-DSpark` | `85ef153be924f17ce4bf62726954eeaa4a73e854` |
| `incoai/Qwen3.8-27B-DFlash2` | `dedf8df68adfb1afeaf7b7480c0a0243108177b4` |
| `Jundot/Qwen3.8-27B-oQ8e-mtp` | `c99e5aad8a478f71c10b9a3dde6709158b690da6` |
| `Jundot/Qwen3.8-27B-oQ8e-fp16-mtp` | `4761782b9455f335292f4d6cb0c89570dff27a11` |

O commit fixado do AWQ inclui a correção do MTP publicada em `c5839cc642e479b7bbcd28311a4b8b9fb52fbd02`.
Não use uma revisão anterior.

Fixe as revisões dos dois drafts antes do download.
Confirme que cada draft usa a mesma família de tokenizer do target.

## Runtimes candidatos

| Runtime | Papel | Porta padrão da campanha |
|---|---|---:|
| `mlx-serve` | Runtime MLX principal | 11234 |
| `llama-server` | Runtime GGUF principal | 8080 |
| `oMLX` | Runtime MLX para AWQ, SpecPrefill e ANE | 8000 |
| `mlx-dspark` | Runtime MLX para DSpark e DFlash 2 | 8484 |

Use um runtime por vez. Termine o processo anterior antes de iniciar outro braço.

## Task runner e dependências

Adicione um `Taskfile.yml` na raiz. Ele deve incluir o Taskfile da campanha sob o namespace `qwen38`.

Instale o runner uma vez em cada máquina:

```bash
brew install go-task
```

O Taskfile não deve instalar outras dependências. Ele deve falhar cedo quando um comando estiver ausente.

| Grupo | Dependências |
|---|---|
| Comum | `python3`, `curl`, `jq`, `git` |
| Rig | Comum, `macmon`, `mlx-serve`, `llama-server`, `omlx`, `mlx-dspark` |
| Driver | Comum, `docker`, `harbor` |

Use estas tarefas durante a campanha:

```text
task qwen38:deps:common
task qwen38:deps:rig
task qwen38:deps:driver
task qwen38:unit
task qwen38:smoke
task qwen38:cache:32k
task qwen38:mtp:32k
task qwen38:omlx:smoke
task qwen38:omlx:cache:32k
task qwen38:omlx:mtp:32k
task qwen38:specprefill:16k
task qwen38:specprefill:32k
task qwen38:ane:16k
task qwen38:ane:32k
task qwen38:dspark:smoke
task qwen38:dspark:decode:8k
task qwen38:dspark:cache:32k
task qwen38:dspark:decode:32k
task qwen38:cache:65k
task qwen38:tool-loop
task qwen38:summary
task qwen38:quality
task qwen38:tbench
task qwen38:validate
```

As tarefas de execução dependem dos checks da máquina correspondente. Elas não devem reinstalar pacotes.

## Configuração base do MLX

Use o comando mínimo documentado pelo model card como braço canônico. Fixe `mlx-serve` em `v26.8.9` ou em revisão posterior registrada, pois essa versão corrige a restauração conjunta de prefix cache e histórico MTP:

```bash
mlx-serve \
  --model ddalcu/Qwen3.8-27B-MLX-Serve-8bit \
  --serve \
  --host 0.0.0.0 \
  --port 11234 \
  --ctx-size 65536 \
  --metrics
```

Esse braço preserva os defaults do runtime, inclusive cache, PLD e seleção automática de MTP. Registre os defaults resolvidos no log de inicialização.

Use `--prefix-cache-entries 0 --no-mtp --no-pld` somente no controle frio.
Use `--no-mtp --no-pld` no braço diagnóstico que isola somente o prefix cache.
Não fixe `--mtp-depth` no braço canônico; deixe a calibração específica do Qwen3.8 escolher a profundidade.

Não ative o cache em SSD antes do teste de restart em memória passar.

## Configuração base do GGUF

Use o quant recomendado pela Unsloth como primeiro braço GGUF. Fixe `llama.cpp` em `v0.2.0` (`5a32f7b66ef6cfb3e60deea26e3454cc6ad3438c`) ou em revisão posterior registrada:

```bash
llama-server \
  -hf unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_XL \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 65536 \
  --n-gpu-layers all \
  --flash-attn on \
  --parallel 1 \
  --jinja \
  --reasoning-preserve \
  --chat-template-kwargs '{"preserve_thinking":true,"reasoning_effort":"xhigh"}' \
  --metrics
```

Esse comando mantém os defaults de prompt/KV cache do `llama.cpp`. Use `--no-cache-prompt` somente no controle frio. Adicione estas opções somente no braço MTP:

```bash
--spec-type draft-mtp --spec-draft-n-max 3
```

Ao carregar por `-hf`, confirme no log que o sidecar `MTP/mtp-Qwen3.8-27B-Q4_0.gguf` foi resolvido e que o runtime reporta drafts gerados e aceitos. Se a revisão fixada não fizer autodiscovery, forneça o sidecar com `--spec-draft-hf unsloth/Qwen3.8-27B-GGUF` e registre essa diferença.

O executor deve validar os nomes das opções na revisão fixada do `llama.cpp`.
Uma mudança de opção deve atualizar este runbook antes das medições.

## Configuração base do oMLX

Use `oMLX` v0.6.3 quando a versão estável estiver disponível antes da primeira medição.
Caso contrário, fixe exatamente `v0.6.3rc2` e marque todos os resultados como experimentais.
Não misture revisões do `oMLX` na mesma comparação.

A versão mínima precisa conter a correção da estimativa de memória KV para o Qwen híbrido.
Ela também precisa conter a correção do cache estático com SpecPrefill.

Inicie o runtime com estado isolado da configuração pessoal:

```bash
OMLX_BASE_PATH="$PWD/bench/qwen3.8-prefix-cache/logs/omlx/<run-id>" \
OMLX_MODEL_DIR="/caminho/para/modelos" \
OMLX_PORT=8000 \
OMLX_CACHE_ENABLED=true \
omlx serve
```

O launcher deve criar `settings.json` e `model_settings.json` no diretório isolado.
Ele deve gerar esses arquivos a partir de `config/omlx-arms.json`.
Ele não deve alterar `~/.omlx` nem a configuração do aplicativo.

Use estes campos por modelo:

```json
{
  "mtp_enabled": false,
  "specprefill_enabled": false,
  "specprefill_draft_model": null,
  "specprefill_keep_pct": null,
  "specprefill_threshold": 8192,
  "qwen35_ane_prefill_enabled": false
}
```

Use o cache global por `OMLX_CACHE_ENABLED`.
Use `specprefill` no request para confirmar o perfil aplicado.
Use `specprefill_keep_pct` e `specprefill_threshold` no request dos braços M e N.

O prefill pela ANE usa APIs privadas e permanece experimental.
Execute o tuner local antes do braço O.
Registre todas as opções `qwen35_ane_prefill_*` resolvidas.
Não copie proporções publicadas para M3 ou M5.

## Configuração base do mlx-dspark

Fixe `mlx-dspark` em `v0.15.0` (`69cd5c1`) durante toda a comparação.
Essa é a versão mínima porque expõe TTFT, prefill, decode isolado e razão contra o
roofline do Mac por request, além de incluir a adaptação de draft cap para contexto
longo introduzida em `v0.14.0`. Não misture versões numa mesma tabela.

Use somente snapshots locais das três revisões fixadas. O controle sem especulação é:

```bash
mlx-dspark serve \
  --model /caminho/para/mlx-community--Qwen3.8-27B-8bit \
  --mode baseline \
  --host 0.0.0.0 \
  --port 8484 \
  --context-window 65536 \
  --reasoning-effort xhigh
```

O braço P adiciona `--no-prefix-cache`. O braço Q preserva o cache padrão.
Os braços especulativos mantêm o cache padrão e trocam apenas o modo e o drafter:

```text
R: --mode dspark --drafter /caminho/para/RadixArk--Qwen3.8-27B-DSpark --max-draft auto
S: --mode dflash --drafter /caminho/para/incoai--Qwen3.8-27B-DFlash2 --max-draft auto
```

Antes das medições, faça um único probe com `--mode auto` e confirme em `/health`
que o runtime resolve DFlash 2 para esse target. O modo `auto` não cria outro braço:
os resultados canônicos usam R e S explícitos para que a técnica observada não dependa
do registry da versão.

Não copie o draft cap medido em M4 Pro. `--max-draft auto` deve calibrar e adaptar o
cap no M4 Max; registre `draft_cap_resolved` por request. Preserve lookup drafts no
braço canônico porque são parte do default do runtime. Use `--no-lookup-drafts`
somente numa ablação identificada quando for necessário atribuir o ganho ao drafter.

Deixe `--kv-bits` ausente na matriz principal. Uma ablação KV8 só pode ocorrer após
o vencedor passar em 65K, pois quantização do KV altera a comparação de memória e
reprodutibilidade. Não habilite SSD spill antes de o cache em RAM passar; quando
habilitado, direcione `--prefix-cache-dir` para `bench/qwen3.8-prefix-cache/logs/`.

Meça separadamente quatro classes de saída: código, matemática, chat e tool-call JSON.
Cada classe deve produzir pelo menos 512 completion tokens no sweep de decode, salvo
EOS natural. Reporte mediana por classe e agregada; não use somente código para escolher
o runtime.

## Configuração do AWQ misto

Use o AWQ somente no `oMLX`.
O checkpoint contém namespaces `mtp.*` que o loader padrão do `mlx_vlm` interpreta incorretamente.

O checkpoint tem 17,36 GB e usa bits mistos.
Ele usa group size 64 nas projeções principais.
O target também contém uma cabeça MTP reparada.

Os ganhos publicados usam M5 e kernels NAX.
Trate esses números somente como hipótese no M4 Max.

## Configuração do SpecPrefill

SpecPrefill atua no prefill.
MTP e PLD atuam no decode.
O prefill pela ANE muda o dispositivo de cálculo.

Compare cada técnica separadamente antes de combinar técnicas.
Não exija identidade de tokens entre o prefill completo e o SpecPrefill.
Exija correção funcional e recuperação das três chaves.

Use estes perfis iniciais:

| Braço | Draft | Keep | Threshold |
|---|---|---:|---:|
| M | Qwen3.5-2B BF16 | 0,40 | 8.192 |
| N | Qwen3.5-0.8B BF16 | 0,50 | 8.192 |

Use prompts frios únicos para medir o custo completo.
Use um system prompt fixo para medir o cache estático.
O histórico esparso da conversa não deve ser tratado como prefixo integral reutilizável.

## Variáveis controladas

Mantenha estes valores iguais em todos os braços:

- Contexto declarado.
- Prompt e tokens do prompt.
- `preserve_thinking=true`.
- `reasoning_effort=xhigh` no braço canônico. `medium` é permitido somente como ablação identificada.
- Temperatura e parâmetros de sampling.
- Limite de saída.
- Ordem dos tool schemas.
- Quantidade de requests concorrentes.
- Temperatura inicial do rig.
- Número de warmups e repetições.

Use os parâmetros oficiais de thinking:

```text
temperature=1.0
top_p=0.95
top_k=20
min_p=0.0
presence_penalty=0.0
repetition_penalty=1.0
```

Use `temperature=0` somente nos testes de equivalência e diagnóstico.

## Matriz de runtime

| Braço | Runtime | Modelo | Prefix cache | Decode especulativo | SpecPrefill | ANE |
|---|---|---|---:|---:|---:|---:|
| A | `mlx-serve` | `mlx8` | desligado | desligado; PLD desligado | desligado | desligada |
| B | `mlx-serve` | `mlx8` | ligado | desligado; PLD desligado | desligado | desligada |
| C | `mlx-serve` | `mlx8` | default do vendor | default/auto do vendor | desligado | desligada |
| D | `llama.cpp` | `gguf-q4` | desligado | desligado | desligado | desligada |
| E | `llama.cpp` | `gguf-q4` | default do runtime | desligado | desligado | desligada |
| F | `llama.cpp` | `gguf-q4` | default do runtime | `draft-mtp` | desligado | desligada |
| G | `llama.cpp` | `gguf-q6` | default do runtime | `draft-mtp` | desligado | desligada |
| H | `llama.cpp` | `gguf-q8` | default do runtime | `draft-mtp` | desligado | desligada |
| I | `oMLX` | `mlx8` | desligado | desligado | desligado | desligada |
| J | `oMLX` | `awq5` | desligado | desligado | desligado | desligada |
| K | `oMLX` | `awq5` | ligado | desligado | desligado | desligada |
| L | `oMLX` | `awq5` | ligado | ligado | desligado | desligada |
| M | `oMLX` | `awq5` + `draft-2b` | ligado | ligado | ligado | desligada |
| N | `oMLX` | `awq5` + `draft-08b` | ligado | ligado | ligado | desligada |
| O | `oMLX` | `awq5` | desligado | desligado | desligado | ligada |
| P | `mlx-dspark` | `mlx8-dspark` | desligado | `baseline` | desligado | desligada |
| Q | `mlx-dspark` | `mlx8-dspark` | ligado | `baseline` | desligado | desligada |
| R | `mlx-dspark` | `mlx8-dspark` + `draft-dspark` | ligado | DSpark, cap auto | desligado | desligada |
| S | `mlx-dspark` | `mlx8-dspark` + `draft-dflash2` | ligado | DFlash 2, cap auto | desligado | desligada |
| T | `oMLX` | `oq8e` | ligado | MTP ligado | desligado | desligada |
| U | `oMLX` | `oq8e-fp16` | ligado | MTP ligado | desligado | desligada |

Execute primeiro os braços A, B, D e E em 8K. Execute C e F após validar o cache sem MTP. Execute G e H após o Q4 passar os gates funcionais.

Execute I e J em 8K para validar o runtime e o loader.
O braço I pode falhar por incompatibilidade do checkpoint.
Registre a incompatibilidade e continue com J.

Execute K após J.
Execute L após K.
Execute L, M e N em 16K e 32K.
Execute J e O em 16K e 32K.
Execute somente os vencedores do oMLX em 65K.

Os braços M e N combinam MTP com SpecPrefill somente depois do gate isolado de MTP.
Use L como baseline direto de M e N.
Use J como baseline direto de O.

Execute P, Q, R e S em 8K após o smoke do launcher.
Use P contra Q para isolar prefix cache. Use Q contra R e S para comparar decode
e tempo total com o mesmo target, cache e sampling. Avance R e S para 32K somente
quando forem lossless no controle greedy. Em 65K, execute Q e apenas o melhor entre
R e S; mantenha ambos somente quando as medianas de tempo total diferirem menos que 5%.

Não compare diretamente o throughput de `mlx8-dspark` com `mlx8` como se fossem o
mesmo artefato: são conversões 8-bit diferentes. A comparação causal de especulação
é exclusivamente P/Q/R/S. Comparações entre runtimes usam tempo total e qualidade
observada, com revisão e quantização sempre registradas.

Execute T e U como um smoke pareado em 32K depois da fase oMLX já planejada. Use os
mesmos prompts, sampling oficial, cache e MTP dos dois lados; deixe SpecPrefill e ANE
desligados para isolar o checkpoint. T é o candidato de produção no M4. U existe
somente para verificar se o fp16 do benchmark público muda materialmente o resultado.
O benchmark público também usou SpecPrefill, draft 0,8B e ANE, portanto este smoke
não deve ser apresentado como reprodução daqueles números.

## Cenários de cache

| Cenário | Request seguinte | Resultado esperado |
|---|---|---|
| `cold` | Primeiro request | Prefill completo |
| `identical` | Repete o request | Reutiliza quase todo o prefixo |
| `append` | Adiciona 1.024 tokens | Processa somente o sufixo novo |
| `middle_mutation` | Muda 64 tokens no meio | Reprocessa após a primeira mudança |
| `tool_turn` | Adiciona tool call e tool result | Preserva o prefixo histórico |
| `restart_ram` | Reinicia sem cache em SSD | Espera miss após o restart |
| `restart_disk` | Reinicia com cache em SSD | Restaura o prefixo persistido |

Use uma fixture com texto determinístico e sem blocos repetidos.
Insira uma chave verificável em 10%, 50% e 90% do contexto.

## Sequência por contexto

1. Aguarde a temperatura da GPU ficar abaixo de 50 °C.
2. Inicie o runtime com o braço selecionado.
3. Aguarde o warmup padrão do runtime.
4. Execute um request descartável de 512 tokens.
5. Execute três medições por cenário.
6. Salve métricas e logs antes de trocar o braço.
7. Termine o runtime.
8. Aguarde 45 segundos entre runtimes.

Execute 8K primeiro. Avance para 32K somente após todos os braços passarem o smoke test.
Execute 65K somente nos braços aprovados em 32K.

## Medições obrigatórias

Cada registro em `results/*.jsonl` deve conter estes campos:

```json
{
  "schema_version": 3,
  "run_id": "20260821T210000Z-mlx8-B-32768-append-r1",
  "runtime": "mlx-serve",
  "runtime_revision": "v26.8.9",
  "model_id": "ddalcu/Qwen3.8-27B-MLX-Serve-8bit",
  "model_revision": "9f31e8c5",
  "quant": "8bit",
  "context_target": 32768,
  "scenario": "append",
  "repeat": 1,
  "cache_enabled": true,
  "mtp_enabled": false,
  "specprefill_enabled": false,
  "specprefill_draft_model": null,
  "specprefill_draft_revision": null,
  "specprefill_keep_pct": null,
  "specprefill_threshold": 8192,
  "specprefill_selected_tokens": null,
  "specprefill_scored_tokens": null,
  "specprefill_draft_ms": null,
  "specprefill_target_ms": null,
  "static_prefix_cached_tokens": null,
  "ane_prefill_enabled": false,
  "ane_prefill_tuned": false,
  "ane_compiled_mlp_layers": null,
  "ane_compiled_gdn_layers": null,
  "prompt_work_mode": "full",
  "prompt_tokens": 32768,
  "cached_tokens": 31744,
  "prefill_tokens": 1024,
  "cache_hit_ratio": 0.96875,
  "ttft_ms": 0.0,
  "e2e_ms": 0.0,
  "prompt_tps": 0.0,
  "decode_tps": 0.0,
  "completion_tokens": 0,
  "mtp_acceptance": null,
  "speculation_mode": null,
  "drafter_id": null,
  "drafter_revision": null,
  "draft_cap_policy": null,
  "draft_cap_resolved": null,
  "drafted_tokens": null,
  "accepted_tokens": null,
  "accept_length": null,
  "verification_steps": null,
  "decode_speedup_vs_baseline": null,
  "machine_roofline_tps": null,
  "decode_roofline_ratio": null,
  "correct": true,
  "ram_peak_gb": 0.0,
  "swap_delta_gb": 0.0,
  "gpu_temp_start_c": 0.0,
  "gpu_temp_peak_c": 0.0,
  "error": null
}
```

Substitua valores de exemplo pelos valores medidos. Não salve respostas completas em `results/`.

Use `prompt_work_mode` com um destes valores: `full`, `cached` ou `sparse`.
Não compare `prompt_tps` bruto entre prefill completo e sparse.
Compare TTFT, tempo total, memória e correção funcional.

Normalize o bloco `x_mlx_dspark` da resposta e os endpoints `/metrics` e `/machine`
nos campos de especulação acima. Não estime taxa de aceitação a partir do throughput.
Calcule `decode_speedup_vs_baseline` somente no resumo, pareando runtime, target,
revisão, contexto, classe de conteúdo, sampling e limite de saída.

## Diagnóstico do template

O probe deve salvar um hash dos tokens em cada limite lógico:

- System prompt.
- Tool schemas.
- Histórico anterior.
- Bloco de reasoning anterior.
- Tool call anterior.
- Tool result anterior.
- Mensagem atual.

O prefixo do request seguinte deve ser idêntico ao request anterior.
Uma diferença de token antes do sufixo invalida a comparação do runtime.

Salve os tokens completos somente em `logs/`. Salve hashes e limites em `results/`.

## Loop agentic controlado

Use quatro ferramentas simuladas com schemas fixos:

1. `read_fixture(path: string)`
2. `search_fixture(query: string)`
3. `run_fixture_test(name: string)`
4. `record_result(key: string, value: string)`

O loop deve executar 20 tool turns. Cada resultado deve adicionar conteúdo único ao histórico.

O loop passa quando:

- Todas as 20 tool calls usam JSON válido.
- Nenhuma ferramenta é chamada mais de três vezes consecutivas.
- A resposta final contém os quatro valores esperados.
- O cache mantém o prefixo histórico.
- Nenhum turno retorna resposta vazia.

## Gates

### Gate 1 — Correção do cache

- `identical`: `cache_hit_ratio >= 0.95`.
- `append`: `cache_hit_ratio >= 0.90`.
- `tool_turn`: `cache_hit_ratio >= 0.90`.
- `middle_mutation`: o runtime não reutiliza tokens após a mutação.

### Gate 2 — Latência

- O tempo quente deve melhorar pelo menos 5 vezes em 32K e 65K.
- O tempo até o primeiro token deve refletir somente o sufixo novo.
- O braço com cache não pode reduzir o decode em mais de 10%.

### Gate 3 — Estabilidade

- `swap_delta_gb <= 0.5`.
- `ram_peak_gb <= 80`.
- Zero crashes.
- Zero respostas corrompidas.
- Vinte tool turns corretos.

### Gate 4 — MTP

- O MTP deve reduzir o tempo total no prompt de código.
- O MTP não pode reduzir o cache hit.
- O MTP não pode alterar o resultado funcional.
- Desative o MTP quando ele falhar em qualquer requisito.

### Gate 5 — Variantes Unsloth de maior fidelidade

Execute Q6 e Q8 somente se o Q4 recomendado pelo vendor passar os quatro gates anteriores.
Adote Q6 ou Q8 somente quando recuperar falhas reais do Q4 ou produzir ganho mensurável de qualidade que justifique o custo.

### Gate 6 — SpecPrefill

- M ou N deve reduzir TTFT em pelo menos 20% contra L.
- O ganho deve aparecer em 16K e 32K.
- O braço deve recuperar as chaves em 10%, 50% e 90%.
- O braço deve concluir 20 tool turns.
- O system prompt deve permanecer correto após cache hit.
- O braço deve respeitar os limites de memória e swap.
- A comparação aceita texto diferente quando o resultado funcional permanece correto.

Avance o melhor perfil para 65K.
Rejeite o perfil quando o ganho desaparecer ou a qualidade cair.

### Gate 7 — Prefill pela ANE

- O deve reduzir TTFT em pelo menos 5% contra J.
- O ganho deve aparecer em 16K ou 32K.
- O braço não pode alterar o resultado funcional.
- O braço deve respeitar os limites de memória e swap.
- O log deve confirmar programas ANE compilados e operações executadas.

Marque o resultado como inconclusivo quando a ANE não executar operações.
Não combine ANE com SpecPrefill nesta campanha.

### Gate 8 — DSpark e DFlash 2

- R e S devem produzir os mesmos tokens que Q em `temperature=0`, salvo empate
  numérico registrado com logits e resultado funcional idêntico.
- `drafter_id`, `drafter_revision`, `draft_cap_resolved`, `accept_length` e
  `verification_steps` devem estar presentes; ausência de telemetria invalida o braço.
- Em 8K, a mediana agregada de `decode_tps` deve ser pelo menos 25% maior que Q.
- Em 32K, a mediana agregada de `decode_tps` deve ser pelo menos 15% maior que Q.
- O ganho deve ser positivo em pelo menos três das quatro classes: código, matemática,
  chat e tool-call JSON. Nenhuma classe pode ficar mais de 5% abaixo de Q.
- Em 32K, o tempo total do loop quente deve melhorar pelo menos 10% contra Q.
- O braço especulativo não pode reduzir o cache hit nem elevar TTFT quente em mais de 10%.
- O braço deve passar os gates de estabilidade e o loop de 20 tool turns.

Selecione entre R e S pela mediana do tempo total quente em 32K. Use decode isolado
como desempate. Se nenhum passar, mantenha Q como representante do runtime.

### Gate 9 — oQ8e

- T e U devem concluir os três repeats em 32K sem crash, corrupção ou swap material.
- Compare TTFT, tempo total, decode sustentado e qualidade funcional sob a mesma
  configuração oMLX.
- Promova T para as fases longas quando a diferença de desempenho estiver dentro de
  5%, preservando a recomendação BF16 para M3/M4.
- Promova U somente quando houver vantagem maior que 5%, repetível, sem regressão
  funcional ou numérica observável; registre que se trata de uma escolha local do rig.
- Não ative SpecPrefill ou ANE neste gate. Se T sobreviver, essas técnicas continuam
  sendo avaliadas pelos braços isolados já existentes.

## Qualidade barata

Execute esta sequência em todos os candidatos funcionalmente aprovados, antes da seleção final:

1. `jdhodges` tool calling.
2. `Veerman` tool calling.
3. Dez questões fixas do LiveCodeBench.
4. Cinco tarefas fixas do Terminal-Bench 2.0.
5. Needle retrieval em 65K.

Use o mesmo conjunto de questões em todos os braços.
Não selecione questões após observar os resultados.

## Terminal-Bench completo

Execute o Harbor no MacBook Pro. Aponte o client para o servidor no rig.

Use o protocolo do repositório:

```text
dataset: terminal-bench/terminal-bench-2
agent: terminus-2
environment: docker
concurrency: 1
agent-timeout-multiplier: 0.5
```

Execute o conjunto completo somente no vencedor da fase barata.
Execute o segundo colocado somente quando a diferença barata ficar dentro da variância observada.

## Ordem da campanha

```text
preflight e pinning
→ implementação do probe
→ smoke test em 8K
→ cache sem MTP em 32K
→ cache com MTP em 32K
→ smoke do oMLX e loader AWQ em 8K
→ cache e MTP do oMLX em 32K
→ smoke pareado oQ8e BF16/fp16 em 32K
→ SpecPrefill em 16K e 32K
→ prefill ANE em 16K e 32K
→ smoke do mlx-dspark e resolução do modo auto
→ baseline, DSpark e DFlash 2 em 8K
→ cache e decode especulativo do mlx-dspark em 32K
→ braços aprovados em 65K
→ loop agentic de 20 turnos
→ Q4 contra Q6 e Q8 na qualidade barata
→ seleção dos sobreviventes compatíveis
→ smoke test dos sobreviventes compatíveis em 262K
→ Terminal-Bench completo
→ relatório e decisão
```

## Regra de decisão

Correção, estabilidade e qualidade mínima são gates eliminatórios. Entre os braços que
passarem, use estes fatores nesta ordem:

1. Tempo total mediano do loop agentic quente em 32K e 65K.
2. TTFT quente e cache hit após tool calls.
3. Throughput de decode sustentado nas quatro classes de conteúdo.
4. Cauda de latência, memória e ausência de swap.
5. Qualidade barata e Terminal-Bench como proteção contra regressão.
6. Simplicidade operacional e reprodutibilidade da configuração.

Não use um score composto. Um runtime incorreto ou instável não pode vencer por
velocidade, mas diferenças de qualidade dentro da variância não devem ocultar uma
vantagem material de desempenho, que é o objetivo principal desta campanha.

## Artefatos da campanha

| Artefato | Local |
|---|---|
| Runbook | `bench/qwen3.8-prefix-cache/plan.md` |
| Referências | `bench/qwen3.8-prefix-cache/references.md` |
| Scripts | `bench/qwen3.8-prefix-cache/scripts/` |
| Testes | `bench/qwen3.8-prefix-cache/tests/` |
| Resultados destilados | `bench/qwen3.8-prefix-cache/results/` |
| Logs brutos | `bench/qwen3.8-prefix-cache/logs/` |
| Plano de implementação | `docs/superpowers/plans/2026-08-21-qwen3-8-prefix-cache-campaign.md` |
| Entrada do Task runner | `Taskfile.yml` |
| Tarefas da campanha | `bench/qwen3.8-prefix-cache/Taskfile.yml` |

Os logs ficam ignorados pelo Git. Os resultados citados no relatório devem ficar versionados.

## Condição de término

A campanha termina quando estes itens existem:

- Um runtime vencedor.
- Um modelo e quant vencedor.
- Uma configuração de produção reproduzível.
- Um relatório com cache frio, cache quente e tool turns.
- Um resultado do Terminal-Bench para o vencedor.
- Uma decisão explícita sobre MTP.
- Uma decisão explícita sobre SpecPrefill e o draft escolhido.
- Uma decisão explícita sobre prefill pela ANE.
- Uma decisão explícita sobre o AWQ misto de 5,0 bpw.
- Uma decisão explícita sobre Q4, Q6 e Q8.
- Uma decisão explícita entre baseline, DSpark e DFlash 2 no target MLX 8-bit.
- Uma medição separada de TTFT, tempo total e decode sustentado do vencedor.
- Um smoke test em 262.144 tokens para cada sobrevivente compatível, ou uma limitação registrada por hardware/runtime.
