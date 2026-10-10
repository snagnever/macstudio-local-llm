# Etapa G — dados para a página perf-lines (2026-10-09)

**O n2 (mlx-serve 26.10.1) segue o mais rápido em todas as bandas, de 8K a 512K. O MTPLX 2.12.2 serve 128K só com
`--memory-limit max` (15.1 s, 1.71× o n2) e recusa 256K. O ds4 serve até 512K com YaRN, mas o turno quente cresce
com o contexto (61.9 s a 512K).** Na qualidade barata, nenhum runtime fica claramente acima do n2 (1–5 casos; o run do n2 usou outro modo de reasoning provável)
([quality-o1-mtplx.md](quality-o1-mtplx.md)).

Rig: M4 Max 128 GB. Probe e gates da campanha (`temperature 1.0`, `top_p 0.95`, `top_k 20`, reasoning `xhigh`,
4096 tokens), tag `pg`, prime de 64 tokens nos braços MTPLX. Dados: `*-pg.jsonl`, `summary-pg.json`,
`reports-2026-10.json`. Página: `reports/qwen38-flashnext-perf-lines.html`.

## O que cada bloco mediu

| bloco | braços | bandas | reps |
| --- | --- | --- | --- |
| G1 | n2, o1, m1, d1 | 8K | 3 |
| G2 | m1v → m1x (ramo), m1xq, m1s | 128K, 256K | 1–3 |
| G3 | d1 | 128K (3), 256K (1), 512K com YaRN 2.0 (1) | 1–3 |
| G4 | qualidade de o1 e m1x | 128K | 1 |

As bandas de 32K a 512K de n2, o1 e c1 vêm das campanhas anteriores (`fn`, `fnx256`, `yarn2` e setembro).

## Resultado (`T_turno`, s)

| braço | 8K | 32K | 128K | 256K | 512K |
| --- | ---: | ---: | ---: | ---: | ---: |
| **n2** mlx-serve 26.10.1 | **7.8** | **8.2** | **8.8** | **9.8** | **12.9** |
| c1 setembro (26.9.2) | 10.1 | 11.0 | 12.4 | 13.9 | 13.6 |
| o1 oMLX 0.7.0 | 9.4 | 10.1 | 12.1 | 14.5 | — (sem YaRN) |
| MTPLX 2.12.2 | 8.2 (m1) | 8.8 (m1p) | 15.1 (m1x) | HTTP 507 | não rodou |
| d1 ds4 | 12.7 | 12.6 | 16.4 | 30.7 | 61.9 |

Swap delta 0 em todos os grupos servidos.

## MTPLX 2.12.2 no M4 Max 128 GB

| braço | knob | 128K | 256K |
| --- | --- | --- | --- |
| m1v | comando mínimo do vendor | HTTP 400 `context_length_exceeded` | HTTP 400 |
| **m1x** | `--memory-limit max` | **passa: 15.1 s**, cold 458 s, prefill 274 tok/s, decode 70.4, wired 109.7 GB | HTTP 507 |
| m1xq | `--memory-limit max` + `--paged-kv-quantization q8` | — | HTTP 507 |
| m1s | `MTPLX_QSA_PREFILL=1` | falha: `stream_error` em todos os turnos | pulado |

- **Janela do vendor.** O memory plan (`mtplx/memory_plan.py`) dá ao engine o menor de 75% da RAM e RAM − 38 GiB:
  90 GiB em 128 GB. Com 77.3 GiB de pesos, ~3 GiB de transientes e 1 GiB de bank, sobram ~8.7 GiB. O custo por token
  é ~137 KB: KV 24 576 B, auxiliar do QSA 7 872 B e transiente do indexer QSA no prefill 104 448 B (12.75 × chunk
  2048 × 4 camadas). Resultado: 68 238 tokens, alinhado para 65 536. O boot log diz "context window 65536 is
  machine-bound (model supports 262144)".
- **`--memory-limit max`.** O budget sobe para RAM − 16 GiB = 112 GiB, e o fit vai para 237 568 tokens. 128K passa
  nos gates; 256K recusa com HTTP 507 ("exceeds this machine's memory-plan fit of 237568 tokens").
- **KV q8.** O MTPLX desliga o q8 no Flash-Next: "paged KV quantization 'q8' is not supported for this model … its
  QSA attention has no validated quantized-cache lane yet — downgrading to off". A mensagem do 507 ainda sugere q8.
  m1q não rodou; m1xq = m1x.
- **Prefill esparso do QSA.** O knob zera o transiente no plano, mas a 128K o allocator passou do limite
  (`pressure_trim` nível 4, `allocator_fraction` 1.02–1.03) e o guard registrou `allocation_failure_shed` 9 vezes.
  Wired de pico 103.6 GB, swap 0.01 GB; o watchdog de 115 GB não disparou. O modo auto liga o caminho esparso só com
  NAX (M5); o vendor mediu 262K num M5 Max.
- **Prefill do m1x.** 274 tok/s a 128K contra 619 a 32K (m1p) e 759 do n2. A 128K a config também muda (memory max,
  wired 109.7 GB). Hipótese: sem NAX, o MTPLX roda a lane
  densa do indexer QSA, cujo trabalho por chunk de 2048 tokens cresce com o contexto. O guard mostra `scratch_bytes`
  15.76 GB por chunk (`scratch_source` `qsa_itemized`). Não perfilei os kernels.

## ds4 (d1)

- Pesos `antirez/qwen3.8-flash-next-gguf` (`qwen38-q4k`): Q4_K gate/up e MXFP4 down nos experts, 69.7 GiB residente,
  tabela de n-grams BF16 (95.4 GiB) no SSD, MTP embutida.
- Serve todas as bandas. De 32K a 512K, o hit de `append` e `tool_turn` fica ≥ 0.94. O decode fica em 43–54 tok/s. O TTFT do `tool_turn` cresce de 6.4 s a 128K
  para 20 s a 256K e 50 s a 512K; a causa não foi investigada.
- 512K com `DS4_QWEN4_YARN_FACTOR=2.0`: cold 895 s, wired 106.6 GB (acima do alerta de 102 GB), swap 0.
- A 8K o reuso cai: `identical` 0.75, `append` e `tool_turn` 0.54 (os gates de cache valem só a 32K e 128K).

## Outros achados

- **o1 a 8K errou needles** em 2 de 3 `tool_turn` (resposta com `finish_reason: stop`). Nas bandas de 32K a 256K,
  as needles estão certas.
- **"MTP acc" do MTPLX (0.07)** no resumo não é a taxa de aceitação; o campo vem de outro contador do log.

## Incidentes

- Um teste fez `source` do orquestrador real (sem `--lib`) e subiu um n2 8K concorrente às 14:28 UTC. Matei em ~2 min
  e restaurei o `n2-8192-t1.0-pg.jsonl` do backup. O `--lib` agora retorna antes da fila.
- O ramo da G2 olhava só HTTP 507. O m1v recusou com HTTP 400, e a fila pulou m1x e m1q. `refused()` agora conta
  qualquer erro HTTP no cold.
- O `run-etapa-g.sh` da G2 ficou vivo como pai do driver relançado, e a continuação esperou 32 min (19:07–19:39 UTC).
- A primeira bateria de qualidade falhou no import do `datasets` (python do sistema). O `run-quality.sh` agora usa o
  `.venv` do submódulo.

## Limites

- 256K e 512K com 1 rep (d1, n2, o1 256K).
- A 32K o d1 vem do run de gate (1 rep).
- A qualidade usa uma rodada por braço, temperatura 0, e pesos diferentes por braço.
- O MTPLX a 8K usa a config da campanha; a 32K, o m1p da Etapa F; a 128K, o m1x. Uma linha da página mistura três
  configs; o rótulo de cada ponto diz qual.
