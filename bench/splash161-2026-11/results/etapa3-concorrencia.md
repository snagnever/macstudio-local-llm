# Task 3: Concorrência de requests paralelos (2026-11-11/12)

**A 1.6.1 corrige a regressão da 1.6.0. No `k2c2LL` a 256K, o pior stream fica 3.5% acima da 1.5.0 com PLE `auto` e empata com PLE `off`. Na 1.6.0, esse valor subia 65%. A espera por memória cai de 30 s por request na 1.6.0 para 0 s com `auto` e até 2.9 s com `off`. Os dois modos passam a regra "Concorrência". O modo escolhido é `auto`.**

Fila `logs/chain-t123.sh`, das 19:37 de 11/11 às 05:15 de 12/11 (relógio do rig). São 18 boots, todos com `rc=0`, cada um com 1 rep. As tags são `f<N>` para a 1.5.0, `h<N>` para a 1.6.1 com PLE `auto` e `q<N>` para a 1.6.1 com PLE `off`. O `N` é a posição na fila. O `/status` foi gravado a cada 5 s.

## Regra "Concorrência"

Média do pior stream nas 3 reps, contra a média da 1.5.0 na mesma fila. O limite é 1.10.

| braço | contexto | 1.5.0 (`f`) | 1.6.1 `auto` (`h`) | 1.6.1 `off` (`q`) | razão `auto` | razão `off` |
|---|---:|---:|---:|---:|---:|---:|
| `k2c2LL` | 256K | 16.07 s | 16.63 s | 16.03 s | **1.035** | **0.998** |
| `k2c2a` | 128K | 14.63 s | 15.80 s | 15.13 s | **1.080** | **1.034** |

Piores streams por rep: `k2c2LL` f 15.3/14.9/18.0, h 15.2/17.5/17.2, q 15.0/15.0/18.1 s; `k2c2a` f 15.1/13.8/15.0, h 16.8/15.0/15.6, q 14.8/15.9/14.7 s.

**Veredito:** `auto` passa e `off` passa.

## Métricas por modo (média de 3 reps)

| braço | modo | s1 | s2 | decode somado | warm TTFT da tool, s1 / s2 | aux p50 | wired peak |
|---|---|---:|---:|---:|---:|---:|---:|
| `k2c2LL` 256K | 1.5.0 | 15.1 s | 15.4 s | 84.9 tok/s | 1.63 / 4.50 s | 1.94 s | 116.6 GB |
| `k2c2LL` 256K | `auto` | 13.4 s | 16.6 s | 84.4 tok/s | 1.59 / 3.45 s | 2.85 s | 94.9 GB |
| `k2c2LL` 256K | `off` | 13.3 s | 16.0 s | 85.9 tok/s | 1.58 / 3.79 s | 2.71 s | 116.7 GB |
| `k2c2a` 128K | 1.5.0 | 13.8 s | 13.6 s | 93.6 tok/s | 1.58 / 3.52 s | 2.48 s | 115.5 GB |
| `k2c2a` 128K | `auto` | 14.1 s | 14.7 s | 86.8 tok/s | 1.53 / 3.30 s | 2.47 s | 86.6 GB |
| `k2c2a` 128K | `off` | 14.3 s | 14.3 s | 86.9 tok/s | 1.53 / 3.38 s | 2.61 s | 115.4 GB |

- **TTFT da tool:** o s2 fica mais rápido nos dois modos da 1.6.1. A 256K, cai de 4.50 s para 3.45 s com `auto`.
- **Decode somado:** a 256K, empata. A 128K, a 1.6.1 fica 7% abaixo da 1.5.0 nos dois modos. Esse valor explica a razão de 1.080 do `auto` no `k2c2a`.
- **Chamadas auxiliares a 256K:** o p50 sobe de 1.94 s para 2.85 s com `auto` e para 2.71 s com `off`. A 128K, não muda. As chamadas auxiliares não entram na regra.
- **Memória:** com `auto`, o wired peak cai 22 GB a 256K e 29 GB a 128K. O swap Δ fica em 0 em todos os boots.
- **Erros HTTP e stalls:** nenhum.

## Espera por memória

Fonte: o último `/status` de cada boot, em [claims-t3.md](claims-t3.md) e [status-t3-last.jsonl](status-t3-last.jsonl). A 1.5.0 não tem o contador `claim_wait`.

| braço | modo | `claim_wait` máximo | `claim_wait` total | gaps `prefill_unit` | `prefill_unit` | linhas `pending` no log de boot |
|---|---|---:|---:|---:|---:|---:|
| `k2c2LL` 256K | 1.6.0 (splash16) | 30.1 s | 190.3 s | 262 | 217.4 s | 5641 |
| `k2c2LL` 256K | `auto` | 0 | 0 | 100–153 | 81–125 s | 0 |
| `k2c2LL` 256K | `off` | 2.0–2.9 s | 2.8–3.8 s | 81–128 | 66–104 s | 1, 0, 0 |
| `k2c2a` 128K | 1.6.0 (splash16) | 30.3 s | 61.4 s | 169 | 137.5 s | – |
| `k2c2a` 128K | `auto` | 0 | 0 | 70–91 | 56–72 s | 0 |
| `k2c2a` 128K | `off` | 0 | 0 | 86–99 | 69–80 s | 0 |

- **A espera de 30 s sumiu.** Com `auto`, nenhum request espera por memória. Com `off`, a 256K, a espera chega a 2.9 s, porque a tabela PLE ocupa 27 GB de RAM.
- **Os gaps de decode** continuam vindo só de `prefill_unit`, o prefill do outro stream intercalado com o decode. Esse é o comportamento da 1.5.0 também.
- **Os logs de boot da 1.5.0** têm zero linhas `pending`.

## Modo de PLE

| regra | `auto` | `off` |
|---|---|---|
| Task 2, `T_turno` ≤ 1.03 | passa (1.000–1.017) | passa (1.000) |
| Task 3, pior stream ≤ 1.10 | passa (1.035; 1.080) | passa (0.998; 1.034) |
| pior stream no `k2c2LL` | 16.63 s | 16.03 s |

Os dois modos passam. O `off` tem o menor pior stream no `k2c2LL`, mas a diferença é de 3.7%, dentro do empate de 5%. Pela regra do plano, o modo escolhido é **`auto`**, porque ele não precisa de flag. O `auto` também libera de 22 a 29 GB de RAM e não tem espera por memória. As Tasks 4 a 7 rodam com `auto`.

O `off` fica melhor no `k2c2a` a 128K (1.034 contra 1.080). A regra do plano decide só pelo `k2c2LL`, então esse valor fica como observação.

## Desvios e checagens

- **Gate "no overlap" do `summarize_parallel.py`:** falha nos 18 boots, também nos 9 da 1.5.0. O gate mede se as janelas de decode dos dois streams se cruzam. Nesta fila, o decode de um stream sempre cai durante o prefill longo do outro, então as janelas não se cruzam. O decode somado (84–94 tok/s, contra 38–48 tok/s por stream) mostra que os streams rodam juntos. A regra do plano não usa esse gate.
- **Needles:** 6 boots têm um request errado em um stream:
  - `k2c2LL` h8 s1, `append`: truncado em 4096 tokens, não é needle errado.
  - 5 respostas erradas no cenário de código do s2 (`rolling_checksum` 33667 em vez de 32896): 1 na 1.5.0, 1 com `auto`, 3 com `off`. São erros do modelo, e a 1.5.0 também tem um.
  - Contando todos os requests de código do s2: 29/30 na 1.5.0, 29/30 com `auto` e 27/30 com `off`.
- **`summarize_claims.py` no `status-t3.jsonl` global:** acha só 10 boots, porque os boots da 1.5.0 não têm o contador `claim_wait` e não marcam o fim do boot. A tabela usa os arquivos `/status` por boot que o `run-parallel-probes.sh` grava.

Fontes: `k2c2LL-262144-<tag>-{s1,s2,aux}.jsonl`, `k2c2a-131072-<tag>-{s1,s2,aux}.jsonl`, [claims-t3.md](claims-t3.md), [status-t3-last.jsonl](status-t3-last.jsonl). Referência da 1.6.0: [etapa4-concorrencia.md da splash16](../../splash16-2026-11/results/etapa4-concorrencia.md).
