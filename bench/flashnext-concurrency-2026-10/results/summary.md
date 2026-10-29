# Flash-Next, concorrência no driver de 2026-10 — resumo da campanha (2026-10-18)

**Duas sessões funcionam num driver só, mas não ganham tempo.** O mlx-serve 26.10.1 já faz batched decode para o Swift 1.5 com o default `--max-concurrent 1`. A segunda sessão divide o decode com a primeira: cada uma fica ~2× mais lenta, e a vazão total não cresce. O perfil `daily` do launcher não muda. O launcher ganha o perfil `256k` (duas sessões longas, prefix cache de 4 GB) e a variável opcional `FLASHNEXT_MAX_CONCURRENT`.

Página pública: [reports/qwen38-flashnext-concurrency.html](../../../reports/qwen38-flashnext-concurrency.html) (gerada por `scripts/render_report.py`).

Rig: Mac Studio M4 Max 128 GB. Driver: Swift 1.5 (`Dankpaws/Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw` `13839b7`) no mlx-serve 26.10.1. Runbook: [plan.md](../plan.md). Metas e regras de cada task estão no runbook; as decisões tomadas durante a execução estão na seção "Emendas".

## Runtimes que rodaram

| braços | runtime no plano | runtime que rodou | motivo |
| --- | --- | --- | --- |
| todos | mlx-serve 26.10.1 | mlx-serve 26.10.1 | — |
| Etapa 2 | Claude Code no rig | Claude Code 2.1.292 (`claude -p`) | — |

## Decisões

| # | teste | braços | regra | resultado | decisão | fonte |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 streams a 32K e 128K | w1c2, w1c2a | pior stream ≤ 2.0×; gates do `w1c2a` | 32K: 1.76×; 128K: 1.94×; stall de aux a 128K (p95 323 s) | N = 2 aprovado com aviso; o stall vem do prefill longo | [etapa1-sintetica.md](etapa1-sintetica.md) |
| 2 | controle serializado | w1c1x2 | `batch beats queue` nas duas bandas | o `--max-concurrent 1` também faz batch; razão contra o `w1c2a` 1.00–1.06× | `BATCH_BEATS_QUEUE=n/a`; sem default novo | [etapa1-sintetica.md](etapa1-sintetica.md) |
| 3 | 3 e 4 streams | w1c3a, w1c4, w1c4a | igual ao 1 | 3 streams: pior stream 2.37× a 32K e 2.36× a 128K, sem recusa; 4 streams: 2.84× a 32K e 3.85× a 128K, 3 `PrefillDoesNotFit` a 128K | N = 3 e N = 4 reprovados; o máximo é 2 | [etapa1-sintetica.md](etapa1-sintetica.md) |
| 4 | 2 streams a 256K | w1c2L, w1c2m4, w1c2q8, w1c2m4q8 | primeiro braço que passa | `L` (rerun com barreira): recusa e needles 10/12; `q8` recusado; `m4q8` cabe e erra 1 needle; `m4` 1.68× (1.81× contra o controle de 3 reps) | `MODE_256K=m4`: perfil `256k` com cache de 4 GB; KV de 8 bits fora | [etapa1b-256k.md](etapa1b-256k.md), [etapa1c-extras.md](etapa1c-extras.md) |
| 5 | Claude Code em par | cc1, cc2 | `wall_s` ≤ 1.5× o controle | 1.84–2.36× por sessão; zero erros; tarefas feitas; o par termina ~7% depois das duas tarefas em sequência | reprovado no tempo; `daily` sem `--max-concurrent` | [etapa2-claude-code.md](etapa2-claude-code.md) |
| 6 | `--prefill-decode-share` 0.3 e 0.5 | w1c2ap3, w1c2ap5 | tirar o stall sem passar de 2.0× | aux > 60 s igual ao controle (8); cold TTFT dobra (168 → ~320 s) | a flag não entra no launcher | [etapa1c-extras.md](etapa1c-extras.md) |

## Notas

- **Batch sem ganho em contexto longo.** Cada stream sobreposto decodifica a ~38–42 tok/s contra 77–84 tok/s sozinho. Um [benchmark independente](https://github.com/drowzeys/keys-Independent-Bench-MLX-Serve-26.9.7-dev-Qwen3.8-Flash-Next-4bit-8bit-mixed) com o mesmo modelo mostra o mesmo padrão: 1.4× de vazão total com prompts curtos e menos que um stream sozinho a partir de 32K.
- **Stall das chamadas curtas.** Uma chamada `permission` que chega durante o prefill longo de outra sessão (`cold` de 128K: ~165 s; 256K: ~350 s) espera o prefill terminar. O controle `w1c1x2` mostra o mesmo efeito, então ele não vem do `--max-concurrent`. Upstream, o [PR #884](https://github.com/ddalcu/mlx-serve/pull/884) trata esse caso, mas exclui o Flash-Next.
- **Recusas de admissão.** Todas as recusas (`w1c2L`, `w1c2q8`, `w1c4a` a 128K) mostram, na própria mensagem, mais memória livre e devolvível pelo hot cache do que o pedido. Exemplo: `prompt 125549 tokens needs ~6266MB at prefill chunk 512 (the narrowest width tried), ~5968MB available + ~13863MB the hot cache can give back (~17420MB resident, ~3556MB of it pinned by this request's own prefix) — refused before prefill`. Parece um problema da admissão do 26.10.1, parecido com a [issue #528](https://github.com/ddalcu/mlx-serve/issues/528). A causa não foi confirmada e nenhuma issue foi aberta.
- **Barreira de início.** A review final achou que streams de contextos diferentes começavam separados (o fixture de 256K leva ~221 s para montar). O harness ganhou uma barreira, e o `w1c2L` rodou de novo com ela. Nos braços de mesmo contexto, o segundo stream começa 36–355 s depois do primeiro; o veredito usa o pior stream (overlap 1.00), e a razão do primeiro é quase um número solo.
- **Controle de 256K.** 1 rep na Etapa 1b (9.8 s, needles 4/5) e 3 reps nos extras (10.3 s, needles 12/13). A referência do plano (11.1 s) fica alta para este rig hoje.

## O que não foi medido

- O pack iQ `dafff5c` com duas sessões.
- 512K com duas sessões (o perfil `512k` força 1 slot).
- mlx-serve 26.10.2 (o batch em contexto longo e o cache só no SSD são novidades dele) e o PR #884 numa release futura.
- Mais de 4 streams. O N = 3 rodou só com o gerador de aux (`w1c3a`), sem o braço sem gerador.
- Fila real no cliente (lock que serializa os requests): o 26.10.1 não tem chave para desligar o batch.
- Splash com duas sessões: medido em 2026-10-29, ver [splash-concurrency-2026-10](../../splash-concurrency-2026-10/results/summary.md).
- A sessão interativa da Etapa 2 (Step 6), com permissões e títulos reais: fica para o usuário (`scripts/run-claude-pair.sh --interactive-env`).
