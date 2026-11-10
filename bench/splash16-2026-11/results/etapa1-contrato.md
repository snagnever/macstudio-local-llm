# Etapa 1 — contrato da atualização (2026-11-07)

**A 1.6.0 passa em C1 a C6, no teste do proxy e no restart do engine. Na C7, as duas releases se comportam igual: o reuso da resposta depois do corte, anunciado na 1.6.0, não aparece. Isso não é regressão, e a Task 1 passa para a regra do launcher.** O servidor do `k2` a 32768 respondeu a todos os checks nas duas versões.

## API

| check | 1.5.0 | 1.6.0 |
|---|---|---|
| C1 `stop_sequences` string | 200 | 400 `stop_sequences must be an array of strings` |
| C2 `stop_sequences` array | 200 | 200 |
| C3 `stop` de 16385 caracteres | 200 | 400 |
| C4 `chat/completions/count_tokens` | 404 | 55 tokens, igual a `usage.prompt_tokens` |
| C5 request encerrado por stop | `cancelled` +1 | `completed` +1 |
| C6 `/status` | schema 6 | schema 8, com os campos novos; os dois campos removidos não aparecem |

## C7: corte de thinking

Medida intermediária, com `thinking_token_budget` 1024 e tool definida:

| | 1.5.0 | 1.6.0 |
|---|---:|---:|
| tokens de saída do primeiro turno (`max_tokens` 4096) | 4096 | 1470 |

- A 1.6.0 respeita o budget nesse pedido. A 1.5.0 chegou ao `max_tokens`. Uma rodada anterior, sem tool, cortou na 1.5.0 também (1029 tokens). Por isso, a diferença vale só para pedidos com tools.
- A reutilização do KV além do corte ainda não está medida. Em três tentativas, a sonda errou o pedido, e nenhuma delas depõe contra o Splash:
  1. mudou o effort entre os turnos;
  2. mandou uma mensagem de usuário, e os templates da Qwen removem o raciocínio de turnos anteriores;
  3. acrescentou uma tool call à resposta, e o Splash só restaura o KV do estado onde a resposta terminou.
- A quarta versão usa a tool call do próprio modelo:

  | | 1.5.0 | 1.6.0 |
  |---|---:|---:|
  | tool call no primeiro turno | não; inconclusivo | sim |
  | `first_prompt` / saída | 332 / – | 332 / 1099 |
  | `cached` no segundo turno | – | 320 |
  | `second_prompt` | – | 1448 |

  O valor 320 é o prompt do primeiro turno arredondado para o bloco de 32 tokens. A 1.6.0 não reaproveitou nenhum token da resposta. Sem a medida da 1.5.0 e sem um controle sem corte, este resultado não separa o corte de um limite geral de reuso.
- O controle `C7b` repete o fluxo sem budget, e C7 tenta até 3 vezes obter a tool call. Resultado com 3 reps por release (`results/contract-c7-1.5.0.jsonl`, `results/contract-c7-1.6.0.jsonl`):

  | rep | 1.5.0 saída / `cached` / `second_prompt` | 1.6.0 saída / `cached` / `second_prompt` |
  |---:|---|---|
  | 1 | sem tool call; inconclusivo | 1313 / 320 / 1662 |
  | 2 | 1129 / 320 / 1479 | 1213 / 320 / 1562 |
  | 3 | 4096 / 320 / 4547 | 1129 / 320 / 1478 |

  - Nas duas releases, o segundo turno reaproveita só o prompt do primeiro turno (320 de 332 tokens). Nenhum token da resposta entra no cache.
  - A 1.6.0 marca FAIL porque o check espera o reuso anunciado. A 1.5.0 marca pass porque o check não tem essa expectativa nela.
  - A 1.5.0 chegou ao `max_tokens` em 1 de 2 reps válidas. A 1.6.0 cortou nas 3 reps. Isso confirma a diferença do corte com tools.
  - O `C7b` ficou inconclusivo nas 6 tentativas: sem budget, o modelo não fez tool call. A rep 3 da 1.5.0 serve de controle: ela não cortou, gerou 4096 tokens, e o segundo turno reaproveitou só 320. Então nenhuma release reaproveita os tokens da resposta, com ou sem corte.
  - Os JSONL da C7 rep 1 e do `C7b` gravam `pass: true` com `observed.inconclusive`. Desde a revisão final, o `api_contract.py` grava `pass: null` para um resultado inconclusivo e para um check só de registro.
- **Conclusão da C7:** o corte com tools funciona melhor na 1.6.0. O reuso do KV depois do corte não aparece em nenhuma release. A 1.6.0 não fica pior que a 1.5.0.

## Proxy

Com `http_proxy` definido, um servidor com `--api-key` e um `claude` falso:

| versão | hits do launcher no proxy | `has_key` | resultado |
|---|---:|---|---|
| 1.5.0 | 1, `GET /v1/models` | sim | **a chave vai ao proxy**, e o launcher não acha o servidor |
| 1.6.0 | 0 | — | acha o servidor; o agente recebe `NO_PROXY=127.0.0.1,localhost,::1` |

Cada versão tem mais um hit, sem chave: o request de controle que prova que o proxy registra. O valor da chave não aparece nos arquivos de resultado nem nos logs do servidor. O rig não tinha `http_proxy` no ambiente da sessão SSH.

## Restart do engine (1.6.0)

Com SIGKILL no `serve-native` durante um stream:

- o stream termina com um evento de erro `runtime_unavailable` e `[DONE]`;
- as tentativas recebem 503 com `Retry-After`: a primeira `runtime_unavailable`, as seguintes `engine_recovering`. [api.md](https://github.com/incoai/splash/blob/1.6.0/docs/api.md) documenta os dois códigos;
- o primeiro 200 chega a 24.3 s, dentro de 2 × o boot de 30 s;
- o contexto continua 32768.

Fontes: [contract-1.5.0.jsonl](contract-1.5.0.jsonl), [contract-1.6.0.jsonl](contract-1.6.0.jsonl), [proxy-1.5.0.jsonl](proxy-1.5.0.jsonl), [proxy-1.6.0.jsonl](proxy-1.6.0.jsonl), [engine-restart.json](engine-restart.json).
