# Flash-Next, concorrência no Splash 1.5.0 — resumo da campanha (2026-10-29)

**No Claude Code real, duas sessões no Splash 1.5.0 ganham tempo. Na bateria sintética, não.** Cada tarefa de Claude Code sozinha leva ~41 s no Splash, contra 62–75 s no mlx-serve 26.10.1. Com duas sessões juntas, cada uma leva 1.36–1.60× o tempo dela sozinha, e o par termina 24% antes das duas tarefas em sequência. Na bateria sintética, que lê 32K–128K de prompt novo por turno, duas sessões ficam 2.4–2.6× mais lentas, e nenhum braço com N ≥ 2 passa. O driver diário (mlx-serve) não muda nesta campanha. O launcher do Splash passa para a 1.5.0.

Página pública: [reports/qwen38-flashnext-concurrency.html](../../../reports/qwen38-flashnext-concurrency.html), seção "Update" (gerada por `bench/flashnext-concurrency-2026-10/scripts/render_report.py`).

Rig: Mac Studio M4 Max 128 GB. Splash: Swift 1.5 GGUF `IQ4_XS` (`ukisai/Swift-1.5-Qwen3.8-Flash-Next-GGUF` `0142554`) no Splash 1.5.0, porta 8585, `--verify-rows auto`. Controle do mesmo dia: Swift 1.5 MLX 4.7bpw `13839b7` no mlx-serve 26.10.3 (`w1zc*`). Runbook: [plan.md](../plan.md); as decisões tomadas durante a execução estão nas emendas.

## Runtimes que rodaram

| braços | runtime no plano | runtime que rodou | motivo |
| --- | --- | --- | --- |
| `k2c*`, `kcc*` | Splash 1.5.0 | Splash 1.5.0 | — |
| `w1zc*` | mlx-serve 26.10.3 | mlx-serve 26.10.3 | braços opcionais, pedido do usuário |
| Etapa 2 | Claude Code no rig | Claude Code 2.1.292 (`claude -p`) | — |

## Decisões

| # | teste | braços | regra | resultado | decisão | fonte |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 streams a 32K e 128K | k2c2, k2c2a | pior stream ≤ 2.0× | 32K: 2.07–2.43×; 128K: 2.52–2.57×; 1 needle errada a 128K | N = 2 reprovado (`N_APPROVED=1`) | [etapa1-sintetica.md](etapa1-sintetica.md) |
| 2 | controle serializado | k2c1x2 | `batch beats queue` | 32K: batch 0.61× a fila (ganha); 128K: 1.08× (perde) | sem default novo | [etapa1-sintetica.md](etapa1-sintetica.md) |
| 3 | 3 e 4 streams | k2c3a, k2c4, k2c4a | igual ao 1 | 32K: 2.95× (N = 3), 4.19–4.40× (N = 4), needles erradas; 128K: 2.39× (N = 3) | reprovados; N = 4 não rodou a 128K | [etapa1-sintetica.md](etapa1-sintetica.md) |
| 4 | 256K | k2c2L, k2c2LL | primeiro braço que passa | `LL`: 1.89×, 26/26 needles, sem ajuste de memória, stall do cold; `L`: sessão curta 2.48× | `MODE_256K=native`, reprovado só pelo stall; `k2c2Ls` não rodou | [etapa1b-256k.md](etapa1b-256k.md) |
| 5 | `--decode-share` 1.0 e 0 | k2c2ad1, k2c2ad0 | passar de 2.0× para baixo sem perder needles | 1.0: 1.77×, vazão 1.24×, 1 needle errada; 0: 8.28× | não entra no launcher | [etapa1c-extras.md](etapa1c-extras.md) |
| 6 | Claude Code em par | kcc1, kcc2 | `wall_s` ≤ 1.5× o controle | 1.36–1.60× por sessão; zero erros; tarefas feitas; par 24% mais rápido que a sequência | aprovado com aviso (5 de 6 sessões no gate) | [etapa2-claude-code.md](etapa2-claude-code.md) |

## mlx-serve × Splash

Pior stream e `T_turno` absoluto com side requests. Cada servidor tem a razão sobre o seu próprio solo. A coluna do mlx-serve usa o 26.10.3 do mesmo dia para N = 1 e 2, e o 26.10.1 da campanha anterior para N = 3, 4 e 256K.

| banda | N | mlx-serve: pior turno | razão | vazão total | aux p95 | Splash: pior turno | razão | vazão total | aux p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 32K | 1 | 7.9 s | — | — | — | 5.8 s | — | — | — |
| 32K | 2 | 13.8 s | 1.75× | 1.43× | 51.9 s | 14.1 s | 2.43× | 1.34× | 2.8 s |
| 32K | 3 | 18.7 s | 2.37× | — | — | 17.1 s | 2.95× | 1.07× | 2.8 s |
| 32K | 4 | 26.6 s | 3.37× | — | — | 24.3 s | 4.19× | 1.14× | 15.9 s |
| 128K | 1 | 9.0 s | — | — | — | 6.1 s | — | — | — |
| 128K | 2 | 15.6 s | 1.73× | 1.49× | 183.0 s | 15.4 s | 2.52× | 0.81× | 5.0 s |
| 128K | 3 | 20.3 s | 2.36× | — | — | 14.6 s | 2.39× | 1.47× | 9.3 s |
| 256K | 2 × 256K | 18.6 s | 1.68× | — | ~356 s | 12.1 s | 1.89× | 1.85× | 8.3 s |
| Claude Code | par ÷ sequência | 148 / 138 s | 1.07 | — | — | 61.7 / 81.5 s | 0.76 | — | — |

O pior turno do mlx-serve 26.10.1 é a razão vezes a referência daquela campanha (7.9 / 8.6 / 11.1 s). A 256K o mlx-serve só cabe com o prefix cache reduzido a 4 GB (`w1c2m4`).

## Notas

- **O prefill decide.** O Splash faz o decode de várias sessões num batch, mas lê um prompt por vez. Quando cada turno traz muito prompt novo (a bateria sintética), a outra sessão espera o prefill, e a razão passa de 2×. Quando o prompt está quase todo em cache (Claude Code: mediana de 575 tokens novos por request), o batch ganha.
- **Requests curtos não ficam presos.** O aux p95 do Splash fica entre 2.8 e 16 s em todas as bandas com side requests. No mlx-serve ele chega a 183–356 s a 128K e 256K, porque a chamada curta espera o prefill longo da outra sessão.
- **"No overlap" é efeito da medida.** O gate conta só as janelas de decode que se cruzam. No Splash um turno decodifica em ~5 s, e o `/status` mostra as sessões ativas ao mesmo tempo (uma em decode, outra em prefill).
- **Controle serializado corrigido.** O probe não contava a espera pelo lock no TTFT (fix `27c48ff`). A rodada de 128K já usou o fix; a de 32K rodou de novo no fim da fila.
- **Needles.** O batch muda os tokens com `--verify-rows auto` e MoE GGUF. As needles erram 1 em 13 em alguns streams com N ≥ 2. O `k2c2v` (`--verify-rows all`) não rodou, porque a diferença fica dentro do ruído de 3 reps.

## O que não foi medido

- `k2c2v` (`--verify-rows all`) e 4 sessões a 128K.
- `--decode-share` na bateria de Claude Code.
- 512K e 1M com duas sessões.
- mlx-serve 26.10.3 com N = 3, 4 e 256K.
- A sessão interativa de Claude Code, com permissões e títulos reais.
- Qualidade de agente (Terminal-Bench) no Splash com duas sessões.
