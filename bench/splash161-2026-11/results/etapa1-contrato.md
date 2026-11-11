# Task 1: Contrato da atualização (2026-11-11)

**A 1.6.1 passa em C1 a C6, no teste do proxy e no restart do engine. Na C7, ela se comporta como a 1.6.0 e a 1.5.0: o turno seguinte não reusa os tokens da resposta. Para a regra do launcher, a Task 1 passa.** Os resultados da 1.5.0 e da 1.6.0 vêm da [Task 1 da splash16](../../splash16-2026-11/results/etapa1-contrato.md).

Braço `k2h` a 32768, PLE `auto`. Fila `logs/chain-t123.sh`, das 15:06 às 15:10 (relógio do rig).

## API

| check | 1.6.0 (splash16) | 1.6.1 |
|---|---|---|
| C1 `stop_sequences` string | 400 `stop_sequences must be an array of strings` | igual |
| C2 `stop_sequences` array | 200 | 200 |
| C3 `stop` de 16385 caracteres | 400 | 400 |
| C4 `chat/completions/count_tokens` | 55, igual a `usage.prompt_tokens` | 55, igual |
| C5 request encerrado por stop | `completed` +1 | `completed` +1 |
| C6 `/status` | schema 8, com os campos novos | schema 8, com os campos novos |
| C7 reuso depois do corte de thinking | `cached` 320 de 332 tokens do primeiro prompt | `cached` 320; saída do primeiro turno 1689 tokens |

- **C7:** o check marca FAIL porque espera o reuso que as notas da 1.6.0 anunciam. A splash16 mostrou o mesmo valor em 3 reps da 1.6.0 e na 1.5.0. Por isso, a C7 não é regressão. A 1.6.1 rodou 1 rep.
- **Campos novos do `/status`,** todos presentes e com valor zero ou quase zero depois do contrato: `console.dropped_lines` 0, `memory_governor.count_checks` com `covered`, `overcounted` e `short_releases` em 0, `metal.pipelines_created_while_serving` 0, `kv_spill.releases` 0, `kv_spill.released_pages` 0, `tokenizer_cache.misses` 1 e `tokenizer_cache.evictions` 0.

## Proxy

Com `http_proxy` definido, um servidor com `--api-key` e um `claude` falso:

| versão | hits do launcher no proxy | resultado |
|---|---:|---|
| 1.5.0 (splash16) | 1, `GET /v1/models`, com chave | a chave vai ao proxy |
| 1.6.0 (splash16) | 0 | o agente recebe `NO_PROXY=127.0.0.1,localhost,::1` |
| 1.6.1 | 0 | o agente recebe `NO_PROXY=127.0.0.1,localhost,::1` |

O único hit da 1.6.1 é o request de controle (`GET /ready`, sem chave), que prova que o proxy registra. O valor da chave de teste não aparece nos arquivos de resultado nem no log do servidor.

## Restart do engine

Com SIGKILL no `serve-native` durante um stream:

- o stream termina com um evento de erro `runtime_unavailable`;
- as 13 tentativas antes do 200 recebem 503 com `Retry-After`: a primeira `runtime_unavailable`, as outras `engine_recovering`;
- o primeiro 200 chega a 13.1 s, contra 24.3 s na 1.6.0, dentro de 2 × o boot de 30 s;
- o contexto continua 32768;
- o servidor não sai com exit 69, porque o engine volta.

O `engine-restart-161.json` grava `verdict` e não grava `pass`; os 4 checks do log da fila passam.

## Desvios

- **Tracebacks do `attach_memory.py`:** os braços com `--exec` não gravam o JSONL de `cache_probe`, então esse passo não acha o arquivo. As filas da splash16 tinham o mesmo caso. Não muda o resultado.

Fontes: [contract-161.jsonl](contract-161.jsonl), [status-161-contract.json](status-161-contract.json), [proxy-1.6.1.jsonl](proxy-1.6.1.jsonl), [proxy-1.6.1-agent-env.txt](proxy-1.6.1-agent-env.txt), [engine-restart-161.json](engine-restart-161.json).
