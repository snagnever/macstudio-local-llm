# Task 4: Concorrência (2026-11-07/08)

**A 1.6.0 tem uma regressão em duas sessões de 256K.** No controle do mesmo dia, o pior stream do `k2c2LL` sobe de 14.8 s na 1.5.0 para 24.4 s na 1.6.0, uma piora de 65%. A causa provável é a espera por memória do governador novo. Ela chega a 30 s por request e só aparece na 1.6.0. Os outros braços não pioram, e as sessões do Claude Code ficam mais rápidas na 1.6.0.

Para a regra "Trocar o launcher", a Task 4 **falha** no `k2c2LL`. O rascunho do relato upstream está em [etapa4-relato-upstream.md](etapa4-relato-upstream.md) e não foi publicado.

## Requests paralelos

Referência: tag e1 da [splash-concurrency-2026-10](../../splash-concurrency-2026-10/results/), na 1.5.0, de outro dia. O `k2c2LL` também tem um controle na 1.5.0 no mesmo dia (tag c1, 1 rep, `results/c150/`).

| braço | contexto | 1.5.0, e1 | 1.5.0, controle | 1.6.0 (3 reps) | leitura |
|---|---:|---|---|---|---|
| `k2c1` | 32K | 5.8 s | – | 6.1 s | dentro de 10%; a Task 2 deu paridade no mesmo dia |
| `k2c1` | 128K | 6.1 s | – | 6.2 s | dentro de 10% |
| `k2c2a` pior stream | 32K | 2.43× | – | 11.4 s, 1.87× | melhor na 1.6.0 |
| `k2c2a` pior stream | 128K | 15.4 s, 2.52× | – | 12.5 s, 2.02× | melhor na 1.6.0; um stall > 60 s |
| `k2c2LL` s1 / s2 | 256K | 12.1 / 8.2 s | 14.2 / 14.8 s | 17.4 / 24.4 s | **pior na 1.6.0** |
| `k2c2LL` decode somado | 256K | 201.3 tok/s | 89.8 tok/s | 86.5 tok/s | igual no mesmo dia |
| `k2c2LL` warm TTFT da tool, s1 / s2 | 256K | – | 1.7 / 4.3 s | 4.1 / 13.8 s | pior na 1.6.0 |

- O decode somado de 201 tok/s da referência e1 não se repete no mesmo dia na 1.5.0. A queda de decode de cerca de 2× da primeira leitura vem do dia, não da release.
- A piora que fica é o TTFT. Na 1.6.0, o turno de tool do s2 teve TTFT de 2.2, 25.0 e 13.8 s nas 3 reps. Na 1.5.0, teve 4.3 s em 1 rep.
- Nenhuma release teve erro HTTP. Needles: 13/13 na 1.6.0 e 5/5 no controle.
- O controle tem 1 rep, como o plano pede.

## Espera por memória na 1.6.0

Fonte: `results/status-t4.jsonl`, último `/status` de cada boot. `claim_wait` é a parte do TTFT que o request passa esperando memória.

| braço | contexto | `claim_wait` máximo | `claim_wait` total | gaps `prefill_unit` |
|---|---:|---:|---:|---|
| `k2c1` | 32K, 128K | 0 | 0 | 0 |
| `k2c2a` | 32K | 0 | 0 | 144, 112.9 s |
| `k2c2a` | 128K | 30.3 s | 61.4 s | 169, 137.5 s |
| `k2c2LL` | 256K | 30.1 s | 190.3 s | 262, 217.4 s |
| `rc*` | 131072 | 0 | 0 | 35–643 por boot |

- O log de boot do `k2c2LL` na 1.6.0 tem 5641 linhas `pending` de pedidos de memória. Os logs do `k2c2LL` na 1.5.0 têm zero, no baseline e no controle.
- A espera aparece só com duas sessões de 128K ou mais. O máximo de cerca de 30 s se repete nos dois braços e sugere um timeout fixo.
- Os gaps de decode vêm só de `prefill_unit`, o prefill de outra sessão intercalado com o decode. Nenhum gap vem de `claim_wait`.

## Sessões do Claude Code

Tarefas c e d, contexto 131072. O controle da 1.5.0 tem 2 reps por perfil. A 1.6.0 tem 3.

| perfil | métrica | 1.5.0, baseline do plano | 1.5.0, controle | 1.6.0 |
|---|---|---|---|---|
| sozinho | warm TTFT p50 / p90 | – | – | 0.9 / 1.6 s |
| par (`rc2`) | wall do par | – | 398.6 s | 321.4 s |
| par (`rc2`) | warm TTFT p50 / p90 | 1.4 / 4.8 s | 1.7 / 3.7 s | 0.9 / 2.6 s |
| par (`rc2`) | warm tok/s p50 / mín | 89.2 / 39.0 | 98.1 / 35.6 | 98.1 / 28.9 |
| subagents (`rc2s`) | wall | – | 969.9 s | 724.4 s |
| subagents (`rc2s`) | warm TTFT p50 / p90 | 2.5 / 8.4 s | 3.2 / 11.7 s | 1.4 / 4.6 s |
| subagents (`rc2s`) | warm tok/s p50 / mín | 82.8 / 20.1 | 77.1 / 23.6 | 90.5 / 15.4 |

- Na 1.6.0, o par termina 19% mais cedo, e os subagents terminam 25% mais cedo. O TTFT p50 e o p90 também ficam menores.
- Só o tok/s mínimo fica pior na 1.6.0: 19% no par e 35% nos subagents. Esse valor vem de um único request por perfil.
- Ruling: as sessões do Claude Code passam. O tempo das sessões e os percentis medem o uso real. O mínimo fica só como observação.
- Tarefa cumprida: 8 de 8 sessões no controle e 15 de 16 na 1.6.0 (com as 4 sessões sozinhas). A sessão que falhou é um `d` do `rc2s` r2, pela checagem oculta do trabalho. O baseline da 1.5.0 teve uma falha igual.
- Nenhum request deu erro HTTP.

## Conclusão

- **Regressão confirmada:** duas sessões de 256K ficam até 65% mais lentas no pior stream da 1.6.0, pela espera por memória de até 30 s.
- **Sem regressão:** um stream, duas sessões de 32K e 128K, e as sessões do Claude Code a 131072.
- O `k2c2a` a 128K também tem espera por memória na 1.6.0, mas mesmo assim fica melhor que o baseline.
- Para a regra "Trocar o launcher", a Task 4 falha. O driver diário fica na 1.5.0, a menos que o usuário decida aceitar essa regressão.
