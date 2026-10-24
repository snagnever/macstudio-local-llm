# Splash 1.4.0: de onde vem a velocidade e o que ela custa (2026-10-24)

No rig, o Splash 1.4.0 com o Swift 1.5 IQ4_XS (`k2a`) faz `T_turno` 0.72–0.75 × o `w1` e 0.64 a 256K. A qualidade fica igual, mas 1 de 5 sessões falhou no probe de tool calls ([etapa8](../bench/stack-updates-2026-10/results/etapa8-splash-swift.md)). Esta nota junta o que a documentação do Splash e do DFlash 2 diz sobre a origem desse ganho e sobre os custos. Ela não roda testes novos.

**Procedência.** As fontes são o README e o `DEVELOPMENT.md` do repositório `incoai/splash` (ramo `main` em 24/10), o post do DFlash 2 da Inco, o post do LM Studio e uma matéria da RuntimeWire. Todas são **terceiro**, e quase todos os números são da própria Inco. A busca não achou relato de terceiros sobre o Swift 1.5 no Splash. Os números do rig são **medido-no-rig**.

## De onde vem a velocidade

| fonte do ganho | o que o Splash faz | evidência no rig |
|---|---|---|
| Speculative decoding com DFlash 2 | Um draft de 5 camadas propõe um bloco de 8 linhas (a âncora e 7 propostas) num só passe. Um seletor guarda 16 candidatos por posição e escolhe o caminho mais coerente entre pares vizinhos. O alvo verifica o bloco num passe. | O draft aceita 3.6–3.8 tokens por ciclo a 128K. O MTP do mlx-serve aceita 0.69–0.78 de 1 token proposto. |
| Kernels Metal por modelo | Cada família tem kernels escritos para as suas formas. Os pesos são convertidos para o layout dos kernels no load. Num ciclo de 8 linhas, o Flash-Next roteia ~43 experts por camada. Um passe de verificação lê esses experts uma vez. | Decode de 107–113 tok/s contra 83 do `w1` a 32K. |
| Atenção esparsa (QSA) | Depois de 512 blocos de 4 tokens, cada query lê só os 512 blocos que o indexer escolhe. | O decode fica em 110 tok/s a 256K. O `w1` cai de 83 para 65 tok/s. |
| KV cache em int8 | `--kv-format int8` é o padrão. Ele usa metade da memória do bf16 e lê menos bytes por token. | — |
| Orçamento de verificação (`--verify-rows auto`) | Num alvo MoE, cada ciclo só verifica as linhas que valem o custo. As outras linhas não roteiam experts. A Inco mede 2–9% de ganho. | `k2a` 2–5% mais rápido que o `k2`. |

O prefill não acelera. A Neural Engine só ajuda alvos densos, e o Flash-Next é MoE. No rig, o cold TTFT do Splash empata com o do `w1` (34.7 contra 34.5 s a 32K, 351 contra 350 s a 256K). O ganho é todo no decode.

## O que a velocidade custa

1. **Determinismo.** Com `--verify-rows auto` num alvo MoE, o mesmo request greedy ou com seed muda de texto entre runs, mesmo sozinho num servidor ocioso. O resultado de uma linha depende das linhas que dividem o tile de expert com ela. A distribuição amostrada continua exata. A Inco fechou a #483 como comportamento esperado. Para comparar runs, usar `--verify-rows all`, um request por vez e um `cache_salt` por request.
2. **KV quantizado.** O Splash quantiza o KV para int8 por padrão. O `w1` roda com KV sem quantização. `--kv-format bf16` remove essa diferença, mas dobra a memória do KV e pode ficar mais lento em contexto longo. A campanha não mediu esse modo.
3. **Draft treinado no modelo base.** Um fine-tune da família usa o draft da família. A Inco não publica a aceitação num fine-tune. No Swift 1.5, a aceitação ficou boa (3.6–3.8), então esse custo não apareceu.
4. **Memória.** O draft BF16 e as tabelas do Splash somam memória. O `k2a` ficou em 108–113 GB wired, contra 97–111 GB do `w1`, sem swap até 256K.
5. **Tool calls.**
   - Com `tool_choice: auto`, nada restringe a saída, e o Splash não valida os argumentos contra o schema.
   - Com `tool_choice: required`, a documentação diz que uma grammar restringe a saída. Mesmo assim, o `k2a` respondeu sem tool call no turno 1 de uma sessão com `required`. A documentação não explica esse resultado. Ele pode ser um bug que vale uma issue.
   - Um `repetition_penalty` acima de 1 pode atrasar tool calls, porque o Splash conta os marcadores de tool call e de `<think>` do prompt.
6. **API.** O Splash recusa `logprobs: true`, `logit_bias`, `n` > 1 e imagens por URL. O Messages da Anthropic não aceita penalidades. Um request com grammar e `ignore_eos` volta 400.
7. **Formatos.** O Flash-Next só roda em GGUF. A #471 (Swift 1.5 MLX) continua aberta, e um GGUF dividido precisa ficar numa pasta `VARIANT/`.
8. **Operação.**
   - O Splash libera os pesos depois de 10 minutos ocioso (`--idle-release`), e o próximo request espera o load de novo. Um driver diário precisa de `--idle-release off`.
   - Acima de 256K, o Splash liga YaRN, que muda as respostas em todo comprimento.

## O que isso muda nos próximos testes

- A aceleração vem quase toda do draft e dos kernels. Os pesos não mudam, e a perda de qualidade esperada vem só do KV int8 e da ordem de soma. A bateria do Task 8 confirma isso: HumanEval 142 contra 141, LiveCodeBench 47 contra 46.
- O risco para um driver de agentes está nas tool calls. O próximo teste deve:
  - rodar o probe no `k2` e no `k2a` com mais sessões;
  - guardar a resposta que vem sem tool call;
  - repetir com `--kv-format bf16`, para separar o efeito do KV int8.
- Um teste de driver precisa de `--idle-release off`.

## Fontes

- https://github.com/incoai/splash (README)
- https://github.com/incoai/splash/blob/main/DEVELOPMENT.md
- https://github.com/incoai/splash/issues/483, /issues/471
- https://inco.ai/blog/dflash2
- https://lmstudio.ai/blog/splash-engine
- https://runtimewire.com/article/inco-ai-dflash-2-parallel-speculative-decoding
