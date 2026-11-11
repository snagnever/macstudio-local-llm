# Task 3: Envelhecimento do decode (#644) — resultado parcial

**Estado: pulada pelo usuário em 07/11, às 18:02 (relógio do rig).** O run `k3f` do perfil `p` parou na rodada 5. O perfil `q` e a repetição em ordem invertida não rodaram. Sem repetição, nenhum perfil tem veredito final.

Carga: 6 rodadas de 3 sessões novas e simultâneas de ~191040 tokens, `max_tokens` 300, contexto 262144, um boot por run. Resumo de cada run: `scripts/summarize_load.py results/aging-<run>.jsonl`.

## Resultado por run

| run | braço | release | rodadas | sonda pre | sonda fim | sonda ocioso | razão fim/pre | veredito | stall |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| `a-150-r1` | `k2f` | 1.5.0 | 6 de 6 | 99.8 | 99.7 | 96.8 | 1.00 | estável | pass |
| `a-160-r1` | `k2g` | 1.6.0 | 6 de 6 | 100.8 | 92.9 | 106.6 | 0.92 | estável | pass |
| `p-160-r1` | `k3g` | 1.6.0 | 6 de 6 | 99.2 | 102.2 | 93.7 | 1.03 | estável | pass |
| `p-150-r1` | `k3f` | 1.5.0 | 4 de 6 | 97.2 | – | – | – | sem sonda | ver nota |

Sondas em tok/s. Maior gap entre tokens: 0.86 s em todos os runs completos. Nenhum HTTP 500.

**Nota sobre o `p-150-r1`:** os 3 erros da rodada 5 e o `stall=fail` vêm da interrupção, não do servidor. Nas rodadas 1 a 4 as sondas ficaram entre 92.6 e 105.7 tok/s, e o maior gap ficou em 0.47 s.

## `/status` no fim de cada run

| run | `pages_cache` | `pages_free` | `denied_reservations` | `pages_moved` | `state_bytes` | `disk_used` |
|---|---:|---:|---:|---:|---:|---:|
| `a-150-r1` | 26367 | 257 | 153509 | 2025 | 237502464 | 34245967872 |
| `a-160-r1` | 26367 | 257 | 8475 | 1167 | 118751232 | 34359443456 |
| `p-160-r1` | 107928 | 360 | 0 | 0 | 2360868864 | 0 |
| `p-150-r1` (rodada 5) | 73678 | 498 | 0 | 0 | 1677459456 | 0 |

No perfil `a`, as duas releases encheram o pool. A 1.6.0 recusou cerca de 18 vezes menos reservas e moveu menos páginas. No perfil `p`, com `--max-memory 96G`, o pool não chegou ao teto, e nenhuma release recusou reservas nem usou o disco.

## Conclusão

- Nenhum run mostrou queda de decode nem stall. A carga não reproduziu a #644 no rig.
- Para a regra "Trocar o launcher", a Task 3 conta como **sem regressão observada, sem veredito**: o perfil `a` está completo nas duas releases, e o perfil `p` só está completo na 1.6.0.
- A gestão do pool mudou na 1.6.0 (menos recusas e movimentos no perfil `a`). Esse dado vem de um run por release.

## O que não rodou

- `p-150-r1` a partir da rodada 5, com as sondas `fim` e `ocioso`.
- Perfil `q` (`k4f`, `k4g`, `Q2_0` da ISTA). O download do `Q2_0` passa para a Task W0 da [flashnext-weights-2026-11](../../flashnext-weights-2026-11/plan.md).
- Repetição em ordem invertida.
- A parte `metrics.ttft_parts_ms` a 256K não foi extraída.
